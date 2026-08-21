#!/usr/bin/env bash
#
# Set up the crawler on a fresh Debian/Ubuntu LXC container:
# service user, clone in /opt, systemd service + daily timer.
#
# Idempotent -- re-running it updates the units and leaves data alone.
#
#   sudo deploy/install.sh [--repo git@github.com:ramhee98/ai-crawler-ipranges.git]

set -euo pipefail

SERVICE_USER="${SERVICE_USER:-aicrawler}"
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-crawler-ipranges}"
REPO_URL="${REPO_URL:-git@github.com:ramhee98/ai-crawler-ipranges.git}"
BRANCH="${BRANCH:-main}"
UNIT_DIR="/etc/systemd/system"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo) REPO_URL="$2"; shift 2 ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --user) SERVICE_USER="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done

[[ $EUID -eq 0 ]] || die "run as root (sudo $0)"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

log "installing packages"
if command -v apt-get >/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends git python3 ca-certificates openssh-client
else
    command -v git >/dev/null || die "git missing and apt-get unavailable; install git and python3 first"
    command -v python3 >/dev/null || die "python3 missing and apt-get unavailable"
fi

python3 - <<'PY' || die "python3 is older than 3.11"
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY

if id -u "$SERVICE_USER" >/dev/null 2>&1; then
    log "user $SERVICE_USER already exists"
else
    log "creating system user $SERVICE_USER"
    useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

HOME_DIR="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"

log "preparing SSH known_hosts for github.com"
install -d -m 700 -o "$SERVICE_USER" -g "$SERVICE_USER" "$HOME_DIR/.ssh"
if ! grep -q '^github\.com ' "$HOME_DIR/.ssh/known_hosts" 2>/dev/null; then
    ssh-keyscan -t rsa,ecdsa,ed25519 github.com 2>/dev/null >> "$HOME_DIR/.ssh/known_hosts"
    chown "$SERVICE_USER:$SERVICE_USER" "$HOME_DIR/.ssh/known_hosts"
    chmod 600 "$HOME_DIR/.ssh/known_hosts"
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "repository already present in $INSTALL_DIR, fetching"
    sudo -u "$SERVICE_USER" git -C "$INSTALL_DIR" fetch --quiet origin "$BRANCH" || \
        log "fetch failed (deploy key not installed yet?), continuing"
elif [[ "$SCRIPT_DIR" == "$INSTALL_DIR/deploy" ]]; then
    die "$INSTALL_DIR exists but is not a git repository"
else
    log "cloning $REPO_URL into $INSTALL_DIR"
    install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" git clone --quiet --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || \
        die "clone failed -- add the deploy key first, then re-run"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/deploy/update.sh"

log "installing systemd units"
for unit in ai-crawler-ipranges.service ai-crawler-ipranges.timer; do
    sed -e "s|^User=.*|User=$SERVICE_USER|" \
        -e "s|^Group=.*|Group=$SERVICE_USER|" \
        -e "s|/opt/ai-crawler-ipranges|$INSTALL_DIR|g" \
        "$SCRIPT_DIR/$unit" > "$UNIT_DIR/$unit"
done

systemctl daemon-reload
systemctl enable --now ai-crawler-ipranges.timer

cat <<EOF

$(log "done")

Next steps:

  1. Create a deploy key and register it on GitHub with write access
     (Settings -> Deploy keys -> Add deploy key -> "Allow write access"):

       sudo -u $SERVICE_USER ssh-keygen -t ed25519 -N '' \\
            -C ai-crawler-ipranges -f $HOME_DIR/.ssh/id_ed25519
       cat $HOME_DIR/.ssh/id_ed25519.pub

  2. Make sure the clone pushes over SSH so the deploy key is actually used:

       sudo -u $SERVICE_USER git -C $INSTALL_DIR remote set-url origin \\
            git@github.com:ramhee98/ai-crawler-ipranges.git

  3. Optional: copy deploy/env.example to $INSTALL_DIR/deploy/.env and adjust
     the commit identity. Set PUSH=0 there for a first dry test.

  4. Run it once and watch the log:

       sudo systemctl start ai-crawler-ipranges.service
       journalctl -u ai-crawler-ipranges -n 50 --no-pager

  Timer status:  systemctl list-timers ai-crawler-ipranges.timer
EOF
