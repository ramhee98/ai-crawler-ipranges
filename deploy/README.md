# Deployment on an LXC container

The container is a **pure mirror**: it hard-resets to `origin/main`, crawls, commits and
pushes. Nothing is edited there by hand, so a failed run can never leave the repository
in a half-written state.

## Files

| File | Purpose |
| --- | --- |
| `install.sh` | one-shot setup: packages, service user, clone into `/opt`, systemd units |
| `update.sh` | the actual job: sync → crawl → commit → push |
| `ai-crawler-ipranges.service` | `Type=oneshot` unit that runs `update.sh` |
| `ai-crawler-ipranges.timer` | daily at 04:00 UTC with up to 1 h jitter, `Persistent=true` |
| `env.example` | template for `deploy/.env` (git-ignored) |

## Setup

```bash
# In the container, as root:
git clone https://github.com/ramhee98/ai-crawler-ipranges /opt/ai-crawler-ipranges
/opt/ai-crawler-ipranges/deploy/install.sh

# Deploy key with write access (Repo → Settings → Deploy keys → Allow write access):
sudo -u aicrawler ssh-keygen -t ed25519 -N '' -C ai-crawler-ipranges \
     -f /home/aicrawler/.ssh/id_ed25519
cat /home/aicrawler/.ssh/id_ed25519.pub

# Point the clone at SSH so the deploy key is used:
sudo -u aicrawler git -C /opt/ai-crawler-ipranges remote set-url origin \
     git@github.com:ramhee98/ai-crawler-ipranges.git
```

First run without pushing, to confirm everything works:

```bash
printf 'PUSH=0\n' | sudo -u aicrawler tee /opt/ai-crawler-ipranges/deploy/.env
sudo systemctl start ai-crawler-ipranges.service
journalctl -u ai-crawler-ipranges -n 50 --no-pager
sudo -u aicrawler git -C /opt/ai-crawler-ipranges log --stat -1
```

Then remove `PUSH=0` (or set it to `1`) and start the service again.

## Requirements inside the container

- Debian/Ubuntu, `python3` ≥ 3.11 — no third-party Python packages
- outbound HTTPS to the vendor endpoints and outbound SSH (port 22) to `github.com`
- an unprivileged LXC container is fine; no capabilities beyond the defaults are needed

If port 22 is blocked, use `ssh.github.com:443` in `/home/aicrawler/.ssh/config`:

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
```

## Operating it

```bash
systemctl list-timers ai-crawler-ipranges.timer   # when does it run next
journalctl -u ai-crawler-ipranges -f              # live log
systemctl start ai-crawler-ipranges.service       # run now
sudo -u aicrawler /opt/ai-crawler-ipranges/deploy/update.sh   # run by hand, same env
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | all sources refreshed |
| `1` | at least one source was stale — previous data reused, the rest was committed. The unit declares `SuccessExitStatus=1`, so systemd does not mark this a failure. |
| `>1` | the crawler aborted; nothing was committed |

A stale source shows up in the root `metadata.json` under `stale_sources` and in the
commit message body, so `git log` tells you when a vendor's endpoint was down.

### Changing the schedule

Use a drop-in rather than editing the shipped unit:

```bash
sudo systemctl edit ai-crawler-ipranges.timer
```

```ini
[Timer]
OnCalendar=
OnCalendar=*-*-* 03,15:00:00 UTC
```

## Alternative: GitHub Actions

If you would rather not run a container, the same job works as a scheduled workflow —
`python3 -m crawler` plus a commit step, with `permissions: contents: write`. The
container setup exists because it keeps the crawl on your own infrastructure and off
GitHub's shared runners.
