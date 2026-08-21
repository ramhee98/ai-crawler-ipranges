"""Writing the generated tree: .txt lists, metadata.json and the README table."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Iterable

from .ranges import PrefixSet, format_networks
from .sources import UNSUPPORTED, Source, Vendor

log = logging.getLogger(__name__)

MARKER = "ai-crawler-ipranges"
README_BEGIN = "<!-- BEGIN GENERATED SOURCES -->"
README_END = "<!-- END GENERATED SOURCES -->"

LIST_FILES = ("ipv4.txt", "ipv6.txt", "ipv4_merged.txt", "ipv6_merged.txt")


def write_if_changed(path: Path, content: str) -> bool:
    """Write ``content`` only when it differs, so git sees no spurious churn."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_changed(path: Path, payload: dict[str, Any]) -> bool:
    return write_if_changed(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_lists(directory: Path, prefixes: PrefixSet) -> int:
    """Write the four .txt files for one directory. Returns files changed.

    Empty families still get an empty file so every path in the tree exists for
    consumers regardless of whether a vendor has IPv6 today.
    """
    payloads = {
        "ipv4.txt": format_networks(prefixes.sorted_v4),
        "ipv6.txt": format_networks(prefixes.sorted_v6),
        "ipv4_merged.txt": format_networks(prefixes.merged_v4),
        "ipv6_merged.txt": format_networks(prefixes.merged_v6),
    }
    return sum(write_if_changed(directory / name, body) for name, body in payloads.items())


def write_source_dir(
    directory: Path,
    vendor: Vendor,
    source: Source,
    prefixes: PrefixSet,
    creation_time: str | None,
) -> int:
    changed = write_lists(directory, prefixes)
    changed += write_json_if_changed(
        directory / "metadata.json",
        {
            "generated_by": MARKER,
            "vendor": vendor.id,
            "vendor_name": vendor.name,
            "bot": source.id,
            "user_agents": list(source.user_agents),
            "source_url": source.url,
            "source_creation_time": creation_time,
            "note": source.note,
            "counts": prefixes.counts(),
        },
    )
    return changed


def write_vendor_dir(
    directory: Path,
    vendor: Vendor,
    prefixes: PrefixSet,
    per_source: dict[str, str | None],
) -> int:
    changed = write_lists(directory, prefixes)
    changed += write_json_if_changed(
        directory / "metadata.json",
        {
            "generated_by": MARKER,
            "vendor": vendor.id,
            "vendor_name": vendor.name,
            "docs": vendor.docs,
            "note": vendor.note,
            "sources": [
                {
                    "bot": source.id,
                    "url": source.url,
                    "user_agents": list(source.user_agents),
                    "source_creation_time": per_source.get(source.id),
                }
                for source in vendor.sources
            ],
            "counts": prefixes.counts(),
        },
    )
    return changed


def write_root(
    root: Path,
    prefixes: PrefixSet,
    vendor_counts: dict[str, dict[str, int]],
    failures: list[str],
) -> int:
    changed = write_lists(root, prefixes)
    changed += write_json_if_changed(
        root / "metadata.json",
        {
            "generated_by": MARKER,
            "vendors": vendor_counts,
            "counts": prefixes.counts(),
            "stale_sources": sorted(failures),
        },
    )
    return changed


def prune_stale(root: Path, expected: set[Path]) -> list[Path]:
    """Delete directories this tool generated that the registry no longer lists.

    Only directories carrying our own ``generated_by`` marker are removed, so a
    hand-written directory in the repo is never touched.
    """
    removed: list[Path] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("."):
            continue
        if candidate in expected:
            continue
        if not _is_generated(candidate):
            continue
        shutil.rmtree(candidate)
        removed.append(candidate)
        log.info("pruned stale directory %s", candidate.relative_to(root))
    return removed


def _is_generated(directory: Path) -> bool:
    metadata = directory / "metadata.json"
    if not metadata.is_file():
        return False
    try:
        return json.loads(metadata.read_text(encoding="utf-8")).get("generated_by") == MARKER
    except (json.JSONDecodeError, OSError):
        return False


def render_sources_table(
    vendors: Iterable[Vendor],
    stats: dict[str, dict[str, Any]],
) -> str:
    """Build the README table listing every source and its current size."""
    lines = [
        "| Vendor | Bot / User-Agent | Official source | Upstream updated | IPv4 | IPv6 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for vendor in vendors:
        for source in vendor.sources:
            key = f"{vendor.id}/{source.id}"
            entry = stats.get(key)
            if entry is None:
                lines.append(
                    f"| [{vendor.name}]({vendor.docs}) | `{'`, `'.join(source.user_agents)}` "
                    f"| [{_short_url(source.url)}]({source.url}) | _not fetched_ | – | – |"
                )
                continue
            counts = entry["counts"]
            updated = (entry.get("source_creation_time") or "–")[:10]
            lines.append(
                f"| [{vendor.name}]({vendor.docs}) | `{'`, `'.join(source.user_agents)}` "
                f"| [{_short_url(source.url)}]({source.url}) | {updated} "
                f"| {counts['ipv4_prefixes']} | {counts['ipv6_prefixes']} |"
            )

    lines.append("")
    lines.append("### Not included")
    lines.append("")
    lines.append("| Vendor | Crawlers | Why it is missing |")
    lines.append("| --- | --- | --- |")
    for name, bots, reason in UNSUPPORTED:
        lines.append(f"| {name} | `{bots}` | {reason} |")
    return "\n".join(lines)


def update_readme(readme: Path, table: str) -> bool:
    """Replace the generated block in README.md between the marker comments."""
    if not readme.is_file():
        log.warning("%s not found, skipping README update", readme)
        return False
    text = readme.read_text(encoding="utf-8")
    start = text.find(README_BEGIN)
    end = text.find(README_END)
    if start == -1 or end == -1 or end < start:
        log.warning("README markers missing, skipping README update")
        return False
    rebuilt = (
        text[: start + len(README_BEGIN)] + "\n\n" + table + "\n\n" + text[end:]
    )
    return write_if_changed(readme, rebuilt)


def _short_url(url: str) -> str:
    return url.split("://", 1)[-1]
