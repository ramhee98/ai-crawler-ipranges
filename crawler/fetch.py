"""HTTP fetching for upstream range lists. Standard library only."""

from __future__ import annotations

import gzip
import json
import logging
import time
import urllib.error
import urllib.request
import zlib
from typing import Any

log = logging.getLogger(__name__)

# Some vendors (openai.com, bing.com) reject requests without a browser-shaped
# User-Agent, so keep a real one and append the project for transparency.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36 "
    "(+https://github.com/ramhee98/ai-crawler-ipranges)"
)

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
RETRY_BACKOFF = 2.0

# Retrying a 404 or a 403 just wastes time -- only these HTTP codes can plausibly
# succeed on a second attempt.
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 509, 520, 521, 522, 523, 524})


class FetchError(RuntimeError):
    """Raised when a source could not be retrieved or parsed."""


def _decode(raw: bytes, encoding: str | None) -> bytes:
    """Undo Content-Encoding, tolerating servers that gzip without saying so."""
    if encoding in ("gzip", "x-gzip"):
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw, -zlib.MAX_WBITS)
    if raw[:2] == b"\x1f\x8b":  # gzip magic without the header
        return gzip.decompress(raw)
    return raw


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> dict[str, Any]:
    """GET ``url`` and return the parsed JSON object.

    Retries transient failures with a linear backoff. Raises `FetchError` on a
    permanent failure or on a body that is not a JSON object.
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
        },
    )

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = _decode(response.read(), response.headers.get("Content-Encoding"))
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS:
                raise FetchError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
            last_error = exc
            if attempt < retries:
                delay = RETRY_BACKOFF * attempt
                log.warning("%s: HTTP %d (attempt %d/%d, retrying in %.0fs)", url, exc.code, attempt, retries, delay)
                time.sleep(delay)
            continue
        except (urllib.error.URLError, OSError, gzip.BadGzipFile, zlib.error) as exc:
            last_error = exc
            if attempt < retries:
                delay = RETRY_BACKOFF * attempt
                log.warning("%s: %s (attempt %d/%d, retrying in %.0fs)", url, exc, attempt, retries, delay)
                time.sleep(delay)
            continue

        if final_url != url:
            log.debug("%s redirected to %s", url, final_url)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            # A JSON endpoint answering with HTML means the URL moved or the
            # vendor put an error page behind a 200. Do not retry that.
            preview = body[:120].decode("utf-8", "replace")
            raise FetchError(f"{url}: response is not JSON ({exc}); starts with {preview!r}") from exc

        if not isinstance(payload, dict):
            raise FetchError(f"{url}: expected a JSON object, got {type(payload).__name__}")
        return payload

    raise FetchError(f"{url}: giving up after {retries} attempts: {last_error}")
