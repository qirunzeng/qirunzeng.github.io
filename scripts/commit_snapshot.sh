#!/usr/bin/env bash
# Commit only the named snapshots and preserve concurrent remote commits.
set -euo pipefail

message=${1:?Usage: commit_snapshot.sh MESSAGE DATA_FILE...}
shift
if [[ $# -eq 0 ]]; then
  echo "At least one snapshot path is required." >&2
  exit 1
fi

if git diff --quiet -- "$@"; then
  echo "No snapshot change to commit."
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then echo "changed=false" >> "$GITHUB_OUTPUT"; fi
  exit 0
fi

branch=$(git symbolic-ref --quiet --short HEAD)
bot_identity=(-c 'user.name=github-actions[bot]' -c 'user.email=41898282+github-actions[bot]@users.noreply.github.com')
git add -- "$@"
git "${bot_identity[@]}" commit --only -m "$message" -- "$@"

for attempt in 1 2 3; do
  git fetch origin "$branch"
  if ! git "${bot_identity[@]}" rebase "origin/$branch"; then
    git rebase --abort
    echo "Snapshot conflicts with a remote edit; leaving the remote unchanged." >&2
    exit 1
  fi
  if git push origin "HEAD:refs/heads/$branch"; then
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then echo "changed=true" >> "$GITHUB_OUTPUT"; fi
    exit 0
  fi
  echo "Push attempt $attempt failed; will refresh the remote before retrying." >&2
done

echo "Could not publish snapshot after three attempts." >&2
exit 1
