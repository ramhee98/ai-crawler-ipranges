# AI Crawler IP Ranges

Machine-readable IP ranges of the common AI crawlers — GPTBot, ClaudeBot, PerplexityBot,
Google-Extended, Applebot, Bingbot, DuckAssistBot, MistralAI, CCBot — collected from the
**official lists published by the vendors themselves** and refreshed daily.

```bash
# every AI crawler prefix, CIDR-aggregated
curl -sO https://raw.githubusercontent.com/ramhee98/ai-crawler-ipranges/main/ipv4_merged.txt

# just OpenAI's training crawler
curl -s https://raw.githubusercontent.com/ramhee98/ai-crawler-ipranges/main/openai/gptbot/ipv4.txt
```

## Layout

Every directory holds the same four files, so any path is predictable:

| File | Contents |
| --- | --- |
| `ipv4.txt` / `ipv6.txt` | prefixes exactly as published upstream, sorted and deduplicated |
| `ipv4_merged.txt` / `ipv6_merged.txt` | the same set, CIDR-aggregated into the shortest equivalent list |
| `metadata.json` | source URLs, covered user-agents, upstream `creationTime`, prefix counts |

```
ipv4.txt                     ← every vendor combined
ipv4_merged.txt
openai/ipv4.txt              ← all OpenAI bots
openai/gptbot/ipv4.txt       ← one bot
openai/oai-searchbot/ipv4.txt
openai/chatgpt-user/ipv4.txt
anthropic/ipv4.txt           ← single combined feed, no per-bot split
google/common-crawlers/ipv4.txt
...
```

Vendors that publish one combined feed (Anthropic, Apple, Microsoft, DuckDuckGo,
Common Crawl) have no per-bot subdirectories — there is nothing upstream to split.

Use the plain files when you want to mirror upstream exactly, and the `_merged` files
when you are loading prefixes into a firewall or an nginx map and want the smallest set.

## Sources

<!-- BEGIN GENERATED SOURCES -->

| Vendor | Bot / User-Agent | Official source | Upstream updated | IPv4 | IPv6 |
| --- | --- | --- | --- | --- | --- |
| [OpenAI](https://platform.openai.com/docs/bots) | `GPTBot` | [openai.com/gptbot.json](https://openai.com/gptbot.json) | 2025-10-30 | 21 | 0 |
| [OpenAI](https://platform.openai.com/docs/bots) | `OAI-SearchBot` | [openai.com/searchbot.json](https://openai.com/searchbot.json) | 2026-01-02 | 39 | 0 |
| [OpenAI](https://platform.openai.com/docs/bots) | `ChatGPT-User`, `ChatGPT-User/2.0` | [openai.com/chatgpt-user.json](https://openai.com/chatgpt-user.json) | 2026-09-11 | 213 | 0 |
| [Anthropic](https://support.claude.com/en/articles/8896518) | `ClaudeBot`, `Claude-User`, `Claude-SearchBot` | [claude.com/crawling/bots.json](https://claude.com/crawling/bots.json) | 2026-08-18 | 26 | 0 |
| [Perplexity](https://docs.perplexity.ai/guides/bots) | `PerplexityBot` | [www.perplexity.ai/perplexitybot.json](https://www.perplexity.ai/perplexitybot.json) | 2025-02-07 | 8 | 0 |
| [Perplexity](https://docs.perplexity.ai/guides/bots) | `Perplexity-User` | [www.perplexity.ai/perplexity-user.json](https://www.perplexity.ai/perplexity-user.json) | 2025-10-17 | 4 | 0 |
| [Google](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot) | `Googlebot`, `Google-Extended` | [developers.google.com/static/crawling/ipranges/common-crawlers.json](https://developers.google.com/static/crawling/ipranges/common-crawlers.json) | 2026-09-14 | 170 | 147 |
| [Google](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot) | `GoogleOther`, `Google-CloudVertexBot`, `Google-Firebase` | [developers.google.com/static/crawling/ipranges/special-crawlers.json](https://developers.google.com/static/crawling/ipranges/special-crawlers.json) | 2026-09-14 | 136 | 136 |
| [Google](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot) | `Google-NotebookLM`, `GoogleAgent-Mariner`, `FeedFetcher-Google` | [developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json) | 2026-09-14 | 529 | 529 |
| [Google](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot) | `Google-NotebookLM`, `GoogleAgent-Mariner`, `Google-Site-Verification` | [developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json) | 2026-09-14 | 248 | 248 |
| [Apple](https://support.apple.com/en-us/119829) | `Applebot`, `Applebot-Extended` | [search.developer.apple.com/applebot.json](https://search.developer.apple.com/applebot.json) | 2026-07-31 | 33 | 0 |
| [Microsoft](https://www.bing.com/webmasters/help/how-to-verify-bingbot-3905dc26) | `bingbot`, `BingPreview` | [www.bing.com/toolbox/bingbot.json](https://www.bing.com/toolbox/bingbot.json) | 2024-01-03 | 28 | 0 |
| [DuckDuckGo](https://duckduckgo.com/duckduckgo-help-pages/results/duckduckbot/) | `DuckAssistBot` | [duckduckgo.com/duckassistbot.json](https://duckduckgo.com/duckassistbot.json) | 2026-09-01 | 486 | 0 |
| [Mistral AI](https://docs.mistral.ai/) | `MistralAI-Index` | [mistral.ai/mistralai-index-ips.json](https://mistral.ai/mistralai-index-ips.json) | 2026-04-19 | 2 | 0 |
| [Mistral AI](https://docs.mistral.ai/) | `MistralAI-User` | [mistral.ai/mistralai-user-ips.json](https://mistral.ai/mistralai-user-ips.json) | 2025-02-19 | 4 | 0 |
| [Common Crawl](https://commoncrawl.org/ccbot) | `CCBot` | [index.commoncrawl.org/ccbot.json](https://index.commoncrawl.org/ccbot.json) | 2026-08-11 | 4 | 1 |

### Not included

| Vendor | Crawlers | Why it is missing |
| --- | --- | --- |
| Meta | `Meta-ExternalAgent, Meta-ExternalFetcher, facebookexternalhit` | No published list; Meta only documents ASN AS32934 for verification. |
| Amazon | `Amazonbot, Amzn-SearchBot, Amzn-User` | IP pages exist but are JavaScript-rendered HTML with no machine-readable feed. |
| xAI | `Grok crawlers / Twitterbot` | No published IP list and no documented crawler user-agent. |
| ByteDance | `Bytespider` | No published IP list; frequently spoofed. |
| Cohere | `cohere-ai` | No published IP list. |

<!-- END GENERATED SOURCES -->

## Read this before you block anything

- **An IP list is necessary, not sufficient.** User-agent strings are trivially spoofed;
  the ranges here are what lets you tell a real GPTBot from someone claiming to be one.
  For the vendors that recommend it (Google, Common Crawl), pair the range check with a
  forward-confirmed reverse DNS lookup.
- **Google and Microsoft ship no AI-only feed.** `Google-Extended` (Gemini/Vertex
  training) uses the same addresses as plain Googlebot, and Bing's crawl infrastructure
  serves both Bing Search and Copilot grounding. Blocking `google/` or `microsoft/`
  wholesale removes you from those search engines too. If that is not what you want,
  express your preference in `robots.txt` (`Google-Extended`, `Applebot-Extended`)
  instead of at the firewall.
- **Training crawlers and user-triggered fetchers are different things.** `GPTBot`
  crawls for model training; `ChatGPT-User` fetches a page because a person asked a
  question about it. Blocking the latter makes your site invisible to users who are
  trying to reach it. That is exactly why the per-bot directories exist.
- **These lists change.** Anthropic's feed alone moves regularly. Re-fetch on a schedule;
  do not bake a snapshot into an image.

## Usage examples

nginx — deny the training crawlers, keep user-triggered fetches:

```nginx
# generated from openai/gptbot/ipv4_merged.txt + anthropic/ipv4_merged.txt
geo $ai_trainer {
    default 0;
    include /etc/nginx/ai-trainers.conf;   # "1.2.3.0/24 1;" per line
}

server {
    if ($ai_trainer) { return 403; }
}
```

nftables — one named set, refreshed by cron:

```bash
curl -s https://raw.githubusercontent.com/ramhee98/ai-crawler-ipranges/main/ipv4_merged.txt \
  | paste -sd, - \
  | xargs -I{} nft add element inet filter ai_crawlers "{ {} }"
```

Shell — check whether a hit is a verified AI crawler:

```bash
grepcidr -f ipv4_merged.txt <<< "$REMOTE_ADDR" && echo "verified AI crawler"
```

## Running it yourself

Python 3.11+, no third-party dependencies.

```bash
python3 -m crawler                # refresh the whole tree
python3 -m crawler --only openai  # one vendor
python3 -m crawler --dry-run -v   # fetch and report, write nothing
```

Exit code is `1` when any source could not be refreshed. A failed fetch never wipes an
existing list: the committed data and the last known upstream `creationTime` are reused,
the source is recorded under `stale_sources` in the root `metadata.json`, and the run is
flagged.

### Daily updates on an LXC container

[`deploy/`](deploy/) contains a systemd timer that crawls, commits and pushes:

```bash
# as root in the container
deploy/install.sh                             # user, units, timer
runuser -u aicrawler -- ssh-keygen -t ed25519 -N '' -f /home/aicrawler/.ssh/id_ed25519
# add the public key as a deploy key with write access, then:
systemctl start ai-crawler-ipranges.service
journalctl -u ai-crawler-ipranges -f
```

See [deploy/README.md](deploy/README.md) for the details.

## License

[MIT](LICENSE). The IP ranges themselves are published by their respective vendors; this
repository only collects and reformats them.
