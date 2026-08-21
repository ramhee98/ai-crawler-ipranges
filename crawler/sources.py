"""Registry of official, machine-readable AI crawler IP range sources.

Only endpoints published by the vendor itself are listed here. Every endpoint
below serves the same JSON schema that Google established for
``googlebot.json``::

    {"creationTime": "...", "prefixes": [{"ipv4Prefix": "..."}, {"ipv6Prefix": "..."}]}

Vendors without a machine-readable list of their own (Meta, Amazon, xAI,
ByteDance, Cohere) are intentionally absent -- see README.md for details.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """A single upstream IP range list, published as one directory of output."""

    id: str
    url: str
    user_agents: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class Vendor:
    """A company whose crawler ranges get aggregated into one directory."""

    id: str
    name: str
    docs: str
    sources: tuple[Source, ...]
    note: str = ""

    @property
    def has_subdirs(self) -> bool:
        """Per-bot subdirectories only make sense for multi-list vendors."""
        return len(self.sources) > 1


VENDORS: tuple[Vendor, ...] = (
    Vendor(
        id="openai",
        name="OpenAI",
        docs="https://platform.openai.com/docs/bots",
        sources=(
            Source(
                id="gptbot",
                url="https://openai.com/gptbot.json",
                user_agents=("GPTBot",),
                note="Crawls to train foundation models.",
            ),
            Source(
                id="oai-searchbot",
                url="https://openai.com/searchbot.json",
                user_agents=("OAI-SearchBot",),
                note="Indexes pages for ChatGPT search results.",
            ),
            Source(
                id="chatgpt-user",
                url="https://openai.com/chatgpt-user.json",
                user_agents=("ChatGPT-User", "ChatGPT-User/2.0"),
                note="Fetches a page because a user or an action asked for it.",
            ),
        ),
    ),
    Vendor(
        id="anthropic",
        name="Anthropic",
        docs="https://support.claude.com/en/articles/8896518",
        sources=(
            Source(
                id="bots",
                url="https://claude.com/crawling/bots.json",
                user_agents=("ClaudeBot", "Claude-User", "Claude-SearchBot"),
                note="One combined feed; Anthropic does not break it down per bot.",
            ),
        ),
        note="Single combined feed covers training, user fetches and search.",
    ),
    Vendor(
        id="perplexity",
        name="Perplexity",
        docs="https://docs.perplexity.ai/guides/bots",
        sources=(
            Source(
                id="perplexitybot",
                url="https://www.perplexity.ai/perplexitybot.json",
                user_agents=("PerplexityBot",),
                note="Indexes pages for Perplexity search results.",
            ),
            Source(
                id="perplexity-user",
                url="https://www.perplexity.ai/perplexity-user.json",
                user_agents=("Perplexity-User",),
                note="Visits a page in response to a user question.",
            ),
        ),
    ),
    Vendor(
        id="google",
        name="Google",
        docs="https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot",
        sources=(
            Source(
                id="common-crawlers",
                url="https://developers.google.com/static/crawling/ipranges/common-crawlers.json",
                user_agents=("Googlebot", "Google-Extended"),
                note="Google-Extended (Gemini/Vertex training) rides on Googlebot ranges.",
            ),
            Source(
                id="special-crawlers",
                url="https://developers.google.com/static/crawling/ipranges/special-crawlers.json",
                user_agents=("GoogleOther", "Google-CloudVertexBot", "Google-Firebase"),
                note="Includes the Vertex AI and GoogleOther fetchers.",
            ),
            Source(
                id="user-triggered-fetchers",
                url="https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json",
                user_agents=("Google-NotebookLM", "GoogleAgent-Mariner", "FeedFetcher-Google"),
                note="User-triggered fetches from outside Google-owned ranges.",
            ),
            Source(
                id="user-triggered-fetchers-google",
                url="https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json",
                user_agents=("Google-NotebookLM", "GoogleAgent-Mariner", "Google-Site-Verification"),
                note="User-triggered fetches from Google-owned ranges.",
            ),
        ),
        note=(
            "Google publishes no AI-only feed: Gemini training (Google-Extended) and "
            "plain search indexing share the same addresses. Blocking these ranges "
            "blocks Google Search too."
        ),
    ),
    Vendor(
        id="apple",
        name="Apple",
        docs="https://support.apple.com/en-us/119829",
        sources=(
            Source(
                id="applebot",
                url="https://search.developer.apple.com/applebot.json",
                user_agents=("Applebot", "Applebot-Extended"),
                note="Applebot-Extended (Apple Intelligence training) shares these ranges.",
            ),
        ),
    ),
    Vendor(
        id="microsoft",
        name="Microsoft",
        docs="https://www.bing.com/webmasters/help/how-to-verify-bingbot-3905dc26",
        sources=(
            Source(
                id="bingbot",
                url="https://www.bing.com/toolbox/bingbot.json",
                user_agents=("bingbot", "BingPreview"),
                note="Copilot grounding runs on Bing's crawl infrastructure.",
            ),
        ),
        note=(
            "Like Google, Microsoft ships one feed for search and AI grounding. "
            "Blocking it blocks Bing Search."
        ),
    ),
    Vendor(
        id="duckduckgo",
        name="DuckDuckGo",
        docs="https://duckduckgo.com/duckduckgo-help-pages/results/duckduckbot/",
        sources=(
            Source(
                id="duckassistbot",
                url="https://duckduckgo.com/duckassistbot.json",
                user_agents=("DuckAssistBot",),
                note="Fetches pages for DuckDuckGo's AI answers.",
            ),
        ),
    ),
    Vendor(
        id="mistral",
        name="Mistral AI",
        docs="https://docs.mistral.ai/",
        sources=(
            Source(
                id="mistralai-index",
                url="https://mistral.ai/mistralai-index-ips.json",
                user_agents=("MistralAI-Index",),
                note="Indexing crawler for Le Chat.",
            ),
            Source(
                id="mistralai-user",
                url="https://mistral.ai/mistralai-user-ips.json",
                user_agents=("MistralAI-User",),
                note="Fetches a page on behalf of a Le Chat user.",
            ),
        ),
    ),
    Vendor(
        id="commoncrawl",
        name="Common Crawl",
        docs="https://commoncrawl.org/ccbot",
        sources=(
            Source(
                id="ccbot",
                url="https://index.commoncrawl.org/ccbot.json",
                user_agents=("CCBot",),
                note="Corpus widely used as LLM training data. FCrDNS check also advised.",
            ),
        ),
    ),
)


# Vendors that run AI crawlers but publish nothing machine-readable. Kept here so
# the README can state *why* they are missing instead of leaving a silent gap.
UNSUPPORTED: tuple[tuple[str, str, str], ...] = (
    (
        "Meta",
        "Meta-ExternalAgent, Meta-ExternalFetcher, facebookexternalhit",
        "No published list; Meta only documents ASN AS32934 for verification.",
    ),
    (
        "Amazon",
        "Amazonbot, Amzn-SearchBot, Amzn-User",
        "IP pages exist but are JavaScript-rendered HTML with no machine-readable feed.",
    ),
    (
        "xAI",
        "Grok crawlers / Twitterbot",
        "No published IP list and no documented crawler user-agent.",
    ),
    (
        "ByteDance",
        "Bytespider",
        "No published IP list; frequently spoofed.",
    ),
    (
        "Cohere",
        "cohere-ai",
        "No published IP list.",
    ),
)


def vendor_by_id(vendor_id: str) -> Vendor:
    for vendor in VENDORS:
        if vendor.id == vendor_id:
            return vendor
    known = ", ".join(v.id for v in VENDORS)
    raise KeyError(f"unknown vendor {vendor_id!r} (known: {known})")


def all_source_count() -> int:
    return sum(len(v.sources) for v in VENDORS)
