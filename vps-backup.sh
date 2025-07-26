#!/usr/bin/env bash
#
# backup.sh
#
# Usage:
#   vps-backup.sh <absolute-source-dir> <git-repo-url-with-credentials>
#
# Workflow:
#   1) Validate args
#   2) Compute paths
#   3) Fresh clone
#   4) Wipe tree (preserve .git & .github)
#   5) Copy in source
#   6) Commit (allow empty) & push
#   7) Cleanup

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <absolute-source-dir> <git-repo-url>" >&2
  exit 1
fi

SRC_DIR="$1"
REPO_URL="$2"

# 1) Validate
if [[ "${SRC_DIR:0:1}" != "/" || ! -d "$SRC_DIR" ]]; then
  echo "Error: source must be an absolute path to an existing directory" >&2
  exit 2
fi

# 2) Paths
BACKUP_PARENT="$(dirname "$SRC_DIR")"
REPO_NAME="$(basename "$REPO_URL" .git)"
CLONE_DIR="$BACKUP_PARENT/$REPO_NAME"

# 3) Fresh clone
rm -rf "$CLONE_DIR"
git clone "$REPO_URL" "$CLONE_DIR"
cd "$CLONE_DIR"

# 4) Wipe (preserve .git and .github)
shopt -s extglob dotglob
rm -rf -- !(.git|.github)
shopt -u extglob

# 5) Copy
cp -a "$SRC_DIR" .

# 6) Commit & push (always make a commit)
git config user.name  "backup-bot"
git config user.email "backup-bot@example.com"
git add --all

TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
COMMIT_MSG="Backup run at $TIMESTAMP"

# --allow-empty ensures we get a commit even if there are no changes
git commit --allow-empty -m "$COMMIT_MSG"

git push origin HEAD

# 7) Cleanup
cd /
rm -rf "$CLONE_DIR"

echo "Backup complete (commit: $COMMIT_MSG)"
