"""Parsing, validation and CIDR aggregation of IP prefixes."""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

log = logging.getLogger(__name__)

IPv4Net = ipaddress.IPv4Network
IPv6Net = ipaddress.IPv6Network


@dataclass
class PrefixSet:
    """A deduplicated collection of IPv4 and IPv6 prefixes."""

    v4: set[IPv4Net] = field(default_factory=set)
    v6: set[IPv6Net] = field(default_factory=set)

    def __bool__(self) -> bool:
        return bool(self.v4 or self.v6)

    def update(self, other: "PrefixSet") -> None:
        self.v4 |= other.v4
        self.v6 |= other.v6

    @property
    def sorted_v4(self) -> list[IPv4Net]:
        return sorted(self.v4)

    @property
    def sorted_v6(self) -> list[IPv6Net]:
        return sorted(self.v6)

    @property
    def merged_v4(self) -> list[IPv4Net]:
        return collapse(self.v4)

    @property
    def merged_v6(self) -> list[IPv6Net]:
        return collapse(self.v6)

    def counts(self) -> dict[str, int]:
        """Prefix and address totals, used for metadata.json and the README."""
        return {
            "ipv4_prefixes": len(self.v4),
            "ipv6_prefixes": len(self.v6),
            "ipv4_prefixes_merged": len(self.merged_v4),
            "ipv6_prefixes_merged": len(self.merged_v6),
            "ipv4_addresses": sum(net.num_addresses for net in self.v4),
        }


def collapse(networks: Iterable[IPv4Net] | Iterable[IPv6Net]) -> list[Any]:
    """Aggregate adjacent and nested prefixes into the shortest equivalent list."""
    nets = list(networks)
    if not nets:
        return []
    return sorted(ipaddress.collapse_addresses(nets))


def parse_payload(payload: dict[str, Any], origin: str) -> tuple[PrefixSet, str | None]:
    """Read the Google-style ``{creationTime, prefixes[]}`` schema.

    Unparsable entries are logged and skipped rather than failing the whole
    source -- one bad prefix upstream should not drop an otherwise good list.
    Returns the prefixes plus the upstream ``creationTime`` if present.
    """
    raw_prefixes = payload.get("prefixes")
    if not isinstance(raw_prefixes, list):
        raise ValueError(f"{origin}: no 'prefixes' array in payload (keys: {sorted(payload)})")

    result = PrefixSet()
    for entry in raw_prefixes:
        if not isinstance(entry, dict):
            log.warning("%s: skipping non-object prefix entry %r", origin, entry)
            continue
        for key, value in entry.items():
            if key not in ("ipv4Prefix", "ipv6Prefix"):
                continue
            network = _parse_prefix(value, key, origin)
            if network is None:
                continue
            if isinstance(network, IPv4Net):
                result.v4.add(network)
            else:
                result.v6.add(network)

    if not result:
        raise ValueError(f"{origin}: payload contained no usable prefixes")

    creation_time = payload.get("creationTime")
    if creation_time is not None and not isinstance(creation_time, str):
        creation_time = None
    return result, creation_time


def _parse_prefix(value: Any, key: str, origin: str) -> IPv4Net | IPv6Net | None:
    if not isinstance(value, str):
        log.warning("%s: skipping non-string %s %r", origin, key, value)
        return None
    text = value.strip()
    try:
        # strict=False tolerates host bits being set upstream; the value is
        # normalised to its network address below.
        network = ipaddress.ip_network(text, strict=False)
    except ValueError as exc:
        log.warning("%s: skipping invalid %s %r (%s)", origin, key, text, exc)
        return None

    expected_v4 = key == "ipv4Prefix"
    if isinstance(network, IPv4Net) != expected_v4:
        log.warning("%s: %s %r is not %s, keeping it under its real family", origin, key, text, "IPv4" if expected_v4 else "IPv6")
    if str(network) != text:
        log.info("%s: normalised %s %r to %s", origin, key, text, network)
    return network


def format_networks(networks: Iterable[Any]) -> str:
    """Render one prefix per line, newline-terminated, for a .txt output file."""
    lines = [str(net) for net in networks]
    return "".join(f"{line}\n" for line in lines)
