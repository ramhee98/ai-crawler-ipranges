#!/usr/bin/env bash
#
# Set up the crawler on a fresh Debian/Ubuntu LXC container:
# service user, clone in /opt, systemd service + daily timer.
#
# Idempotent -- re-running it updates the units and leaves data alone.
#
#   deploy/install.sh [--repo https://github.com/ramhee98/ai-crawler-ipranges]
#
# Must run as root. Drops to the service user with runuser, so a minimal
# container without sudo installed works.

set -euo pipefail

SERVICE_USER="${SERVICE_USER:-aicrawler}"
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-crawler-ipranges}"
# HTTPS by default: a fresh host has no deploy key yet, so an SSH clone would
# fail. Step 2 of the printed instructions switches the remote to SSH.
REPO_URL="${REPO_URL:-https://github.com/ramhee98/ai-crawler-ipranges}"
BRANCH="${BRANCH:-main}"
UNIT_DIR="/etc/systemd/system"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# Run a command as the service user. runuser ships with util-linux and needs no
# sudo, which a minimal LXC image usually does not have. It execs directly, so
# the account's nologin shell does not get in the way.
as_service_user() {
    if command -v runuser >/dev/null; then
        runuser -u "$SERVICE_USER" -- "$@"
    else
        su -s /bin/sh -c "$(printf '%q ' "$@")" "$SERVICE_USER"
    fi
}

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

[[ $EUID -eq 0 ]] || die "run as root: $0"

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
    as_service_user git -C "$INSTALL_DIR" fetch --quiet origin "$BRANCH" || \
        log "fetch failed (deploy key not installed yet?), continuing"
elif [[ "$SCRIPT_DIR" == "$INSTALL_DIR/deploy" ]]; then
    die "$INSTALL_DIR exists but is not a git repository"
else
    log "cloning $REPO_URL into $INSTALL_DIR"
    install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$INSTALL_DIR"
    as_service_user git clone --quiet --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || \
        die "clone failed -- use an https:// --repo url, or add the deploy key first"
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
systemctl enable ai-crawler-ipranges.timer

# Deliberately not started here: the deploy key is not in place yet, so the
# first run would fail at the push step. Step 4 below starts it.
cat <<EOF

$(log "done -- timer enabled but not started yet")

Next steps (as root):

  1. Create a deploy key and register it on GitHub with write access
     (Settings -> Deploy keys -> Add deploy key -> "Allow write access"):

       runuser -u $SERVICE_USER -- ssh-keygen -t ed25519 -N '' \\
               -C ai-crawler-ipranges -f $HOME_DIR/.ssh/id_ed25519
       cat $HOME_DIR/.ssh/id_ed25519.pub

  2. Point the clone at SSH so the deploy key is actually used, and confirm it:

       runuser -u $SERVICE_USER -- git -C $INSTALL_DIR remote set-url origin \\
               git@github.com:ramhee98/ai-crawler-ipranges.git
       runuser -u $SERVICE_USER -- ssh -T git@github.com

  3. Optional: copy deploy/env.example to $INSTALL_DIR/deploy/.env and adjust
     the commit identity. Set PUSH=0 there for a first dry test.

  4. Run it once, then start the timer:

       systemctl start ai-crawler-ipranges.service
       journalctl -u ai-crawler-ipranges -n 50 --no-pager
       systemctl start ai-crawler-ipranges.timer

  Timer status:  systemctl list-timers ai-crawler-ipranges.timer
EOF
