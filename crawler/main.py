"""Entry point: fetch every official AI crawler range list and write the tree.

    python3 -m crawler                      # refresh everything in the repo root
    python3 -m crawler --only openai        # just one vendor
    python3 -m crawler --dry-run -v         # report without touching files

A source that fails to fetch does not wipe its existing lists: the previous
on-disk data is reused for aggregation, the vendor is reported as stale, and the
process exits non-zero so the systemd timer surfaces it.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .fetch import FetchError, fetch_json
from .output import (
    prune_stale,
    render_sources_table,
    update_readme,
    write_root,
    write_source_dir,
    write_vendor_dir,
)
from .ranges import PrefixSet, parse_payload
from .sources import VENDORS, Source, Vendor, all_source_count, vendor_by_id

log = logging.getLogger("crawler")

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class SourceResult:
    source: Source
    prefixes: PrefixSet
    creation_time: str | None
    stale: bool = False
    error: str | None = None


@dataclass
class Run:
    """Accumulated state of one crawl."""

    changed_files: int = 0
    failures: list[str] = field(default_factory=list)
    stats: dict[str, dict] = field(default_factory=dict)
    vendor_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    total: PrefixSet = field(default_factory=PrefixSet)
    pruned: list[Path] = field(default_factory=list)


def source_dir(root: Path, vendor: Vendor, source: Source) -> Path:
    """Where one upstream list lands. Single-list vendors skip the subdirectory."""
    if vendor.has_subdirs:
        return root / vendor.id / source.id
    return root / vendor.id


def load_existing(directory: Path) -> PrefixSet | None:
    """Recover prefixes already committed to disk, for use when a fetch fails."""
    prefixes = PrefixSet()
    found_any = False
    for name in ("ipv4.txt", "ipv6.txt"):
        path = directory / name
        if not path.is_file():
            continue
        found_any = True
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                network = ipaddress.ip_network(line, strict=False)
            except ValueError:
                log.warning("%s: ignoring unparsable line %r", path, line)
                continue
            if isinstance(network, ipaddress.IPv4Network):
                prefixes.v4.add(network)
            else:
                prefixes.v6.add(network)
    if not found_any:
        return None
    return prefixes


def load_last_creation_time(directory: Path) -> str | None:
    """Recover the upstream timestamp already recorded, so a stale run keeps it."""
    metadata = directory / "metadata.json"
    if not metadata.is_file():
        return None
    try:
        value = json.loads(metadata.read_text(encoding="utf-8")).get("source_creation_time")
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, str) else None


def fetch_source(root: Path, vendor: Vendor, source: Source) -> SourceResult:
    log.info("fetching %s/%s from %s", vendor.id, source.id, source.url)
    try:
        payload = fetch_json(source.url)
        prefixes, creation_time = parse_payload(payload, source.url)
    except (FetchError, ValueError) as exc:
        log.error("%s/%s failed: %s", vendor.id, source.id, exc)
        directory = source_dir(root, vendor, source)
        existing = load_existing(directory)
        if existing:
            log.warning(
                "%s/%s: keeping %d IPv4 / %d IPv6 prefixes already on disk",
                vendor.id,
                source.id,
                len(existing.v4),
                len(existing.v6),
            )
            # Keep the last known upstream timestamp rather than writing null,
            # which would churn the diff on every failed run.
            return SourceResult(
                source, existing, load_last_creation_time(directory), stale=True, error=str(exc)
            )
        return SourceResult(source, PrefixSet(), None, stale=True, error=str(exc))

    log.info(
        "%s/%s: %d IPv4 (%d merged), %d IPv6 (%d merged)",
        vendor.id,
        source.id,
        len(prefixes.v4),
        len(prefixes.merged_v4),
        len(prefixes.v6),
        len(prefixes.merged_v6),
    )
    return SourceResult(source, prefixes, creation_time)


def process_vendor(root: Path, vendor: Vendor, run: Run, dry_run: bool) -> None:
    results = [fetch_source(root, vendor, source) for source in vendor.sources]

    aggregate = PrefixSet()
    creation_times: dict[str, str | None] = {}
    for result in results:
        aggregate.update(result.prefixes)
        creation_times[result.source.id] = result.creation_time
        run.stats[f"{vendor.id}/{result.source.id}"] = {
            "counts": result.prefixes.counts(),
            "source_creation_time": result.creation_time,
            "stale": result.stale,
        }
        if result.stale:
            run.failures.append(f"{vendor.id}/{result.source.id}")

    if not aggregate:
        log.error("%s: no data at all, leaving the directory untouched", vendor.id)
        return

    run.total.update(aggregate)
    run.vendor_counts[vendor.id] = aggregate.counts()

    if dry_run:
        return

    if vendor.has_subdirs:
        for result in results:
            if not result.prefixes:
                continue
            run.changed_files += write_source_dir(
                source_dir(root, vendor, result.source),
                vendor,
                result.source,
                result.prefixes,
                result.creation_time,
            )
    run.changed_files += write_vendor_dir(root / vendor.id, vendor, aggregate, creation_times)


def selected_vendors(only: list[str] | None) -> tuple[Vendor, ...]:
    if not only:
        return VENDORS
    return tuple(vendor_by_id(name) for name in only)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m crawler",
        description="Collect official IP ranges of common AI crawlers.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=REPO_ROOT,
        help="repository root to write the tree into (default: %(default)s)",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="VENDOR",
        help="restrict to one vendor id; repeatable",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch and report, but do not write any file",
    )
    parser.add_argument("--no-prune", action="store_true", help="keep directories the registry no longer lists")
    parser.add_argument("--no-readme", action="store_true", help="do not regenerate the README table")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="-v for info, -vv for debug")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    level = {0: logging.WARNING, 1: logging.INFO}.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format="%(levelname)-7s %(message)s", stream=sys.stderr)

    root: Path = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)

    try:
        vendors = selected_vendors(args.only)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2

    run = Run()
    for vendor in vendors:
        process_vendor(root, vendor, run, args.dry_run)

    partial = bool(args.only)
    if not args.dry_run:
        if not partial:
            run.changed_files += write_root(root, run.total, run.vendor_counts, run.failures)
        if not args.no_prune:
            run.pruned = prune_stale(root, {root / v.id for v in VENDORS})
            for vendor in VENDORS:
                expected = {source_dir(root, vendor, s) for s in vendor.sources}
                vendor_dir = root / vendor.id
                if vendor.has_subdirs and vendor_dir.is_dir():
                    run.pruned += prune_stale(vendor_dir, expected)
        if not args.no_readme and not partial:
            run.changed_files += update_readme(root / "README.md", render_sources_table(VENDORS, run.stats))

    report(run, vendors, partial=partial, dry_run=args.dry_run)
    return 1 if run.failures else 0


def report(run: Run, vendors: tuple[Vendor, ...], *, partial: bool, dry_run: bool) -> None:
    fetched = sum(len(v.sources) for v in vendors)
    scope = f"{fetched}/{all_source_count()} sources" if partial else f"{fetched} sources"
    print(
        f"{scope}: {len(run.total.v4)} IPv4 and {len(run.total.v6)} IPv6 prefixes "
        f"({len(run.total.merged_v4)} / {len(run.total.merged_v6)} merged)"
    )
    if dry_run:
        print("dry run, no file written")
    else:
        print(f"wrote {run.changed_files} changed file(s)")
    if run.pruned:
        print(f"pruned {len(run.pruned)} stale director(ies): {', '.join(p.name for p in run.pruned)}")
    if run.failures:
        print(f"STALE: {len(run.failures)} source(s) could not be refreshed: {', '.join(run.failures)}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
