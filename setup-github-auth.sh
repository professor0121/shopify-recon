#!/usr/bin/env bash
# setup-github-auth.sh - One-time GitHub auth setup for auto-sync.
#
# Stores a GitHub Personal Access Token (PAT) in git's credential store so all
# future `git push` calls (including cron/auto-sync) authenticate silently.
#
# The token is read from the GH_PAT environment variable (NOT a command-line
# arg, so it never lands in shell history or the process list visible to others).
#
# Usage:
#   GH_PAT=ghp_xxxxxxxxxxxx ./setup-github-auth.sh
#
# After running once, ./auto-sync.sh can push forever with no prompts.

set -euo pipefail

REPO_DIR="/home/ubuntu/tools"
GH_USER="krickelsync"
CRED_FILE="$HOME/.git-credentials"

if [ -z "${GH_PAT:-}" ]; then
  echo "ERROR: GH_PAT environment variable not set." >&2
  echo "Run:  GH_PAT=ghp_yourtoken ./setup-github-auth.sh" >&2
  exit 1
fi

cd "$REPO_DIR"

# Enable the file-based credential store globally.
git config --global credential.helper store

# Write the credential line (token embedded). chmod 600 so only the user reads it.
LINE="https://${GH_USER}:${GH_PAT}@github.com"
# Remove any existing github.com line, then append the fresh one.
if [ -f "$CRED_FILE" ]; then
  grep -v 'github.com' "$CRED_FILE" > "${CRED_FILE}.tmp" 2>/dev/null || true
  mv "${CRED_FILE}.tmp" "$CRED_FILE"
fi
echo "$LINE" >> "$CRED_FILE"
chmod 600 "$CRED_FILE"

# Ensure remote uses HTTPS (matches the stored credential).
git remote set-url origin "https://github.com/${GH_USER}/shopify-recon.git"

echo "GitHub auth stored for ${GH_USER}. Verifying with a remote ls..."
if git ls-remote origin -h refs/heads/main >/dev/null 2>&1; then
  echo "OK - authentication works. auto-sync.sh can now push automatically."
else
  echo "WARNING: stored token but remote check failed. Token may lack 'repo' scope or be invalid." >&2
  exit 2
fi
