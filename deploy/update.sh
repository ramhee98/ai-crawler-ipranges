#!/usr/bin/env bash
#
# Refresh the IP range lists and push the result to the origin remote.
# Intended to be driven by ai-crawler-ipranges.timer; safe to run by hand.
#
# The container is treated as a pure mirror of the remote: any local change is
# discarded before crawling, so a half-finished previous run cannot poison the
# history. Override anything below in deploy/.env.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"

[[ -f "$SCRIPT_DIR/.env" ]] && source "$SCRIPT_DIR/.env"

BRANCH="${BRANCH:-main}"
REMOTE="${REMOTE:-origin}"
PYTHON="${PYTHON:-python3}"
GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-ai-crawler-ipranges}"
GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-ai-crawler-ipranges@localhost}"
RESET_LOCAL="${RESET_LOCAL:-1}"
PUSH="${PUSH:-1}"

export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

log() { printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

cd "$REPO_DIR" || die "repository directory $REPO_DIR not found"
git rev-parse --git-dir >/dev/null 2>&1 || die "$REPO_DIR is not a git repository"

if [[ "$RESET_LOCAL" == "1" ]]; then
    log "syncing with $REMOTE/$BRANCH"
    git fetch --quiet "$REMOTE" "$BRANCH" || die "git fetch failed"
    git checkout --quiet "$BRANCH"
    git reset --quiet --hard "$REMOTE/$BRANCH"
    git clean --quiet -fd
fi

log "crawling"
summary_file="$(mktemp)"
trap 'rm -f "$summary_file"' EXIT

crawl_status=0
"$PYTHON" -m crawler --verbose > "$summary_file" || crawl_status=$?
cat "$summary_file"

if (( crawl_status > 1 )); then
    die "crawler aborted with exit code $crawl_status, not committing"
fi
if (( crawl_status == 1 )); then
    log "WARNING: at least one source is stale, committing the rest"
fi

if [[ -z "$(git status --porcelain)" ]]; then
    log "no changes, nothing to commit"
    exit "$crawl_status"
fi

git add --all
stamp="$(date -u +'%Y-%m-%d %H:%M UTC')"
{
    echo "data: update AI crawler IP ranges ($stamp)"
    echo
    cat "$summary_file"
    if (( crawl_status == 1 )); then
        echo
        echo "Note: some sources were stale; previous data reused for those."
    fi
} | git commit --quiet --file=- || die "git commit failed"

log "committed $(git rev-parse --short HEAD)"

if [[ "$PUSH" == "1" ]]; then
    log "pushing to $REMOTE/$BRANCH"
    git push --quiet "$REMOTE" "HEAD:$BRANCH" || die "git push failed"
    log "pushed"
else
    log "PUSH=0, leaving the commit local"
fi

exit "$crawl_status"
