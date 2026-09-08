#!/usr/bin/env bash
# deploy.sh - Install Shopify CLI (if missing) and push a theme to a store
# using a Theme Access app token (shptka_...). No interactive OAuth login.
#
# This is the script an AI agent (Claude Code, Cursor, etc.) or a human runs
# after cloning the repo. It is self-contained: it checks for the CLI, installs
# it if needed, validates the theme, and pushes.
#
# AUTH (Theme Access app):
#   1. In Shopify admin install the free "Theme Access" app.
#   2. Add a user, it emails a password that starts with shptka_.
#   3. Export it before running:
#        export SHOPIFY_CLI_THEME_TOKEN=shptka_xxx
#        export SHOPIFY_FLAG_STORE=yourstore.myshopify.com
#
# USAGE:
#   ./deploy.sh <theme_dir> [--live]      # push (default: unpublished/dev theme)
#   ./deploy.sh ./rothys-clone/theme
#   ./deploy.sh ./rothys-clone/theme --live   # publish to live (asks first)
#
# ENV VARS:
#   SHOPIFY_CLI_THEME_TOKEN   required, the shptka_ token
#   SHOPIFY_FLAG_STORE        required, yourstore.myshopify.com
set -euo pipefail

THEME_DIR="${1:-}"
PUBLISH="${2:-}"

err() { echo "ERROR: $*" >&2; exit 1; }

[ -n "$THEME_DIR" ] || err "Usage: ./deploy.sh <theme_dir> [--live]"
[ -d "$THEME_DIR" ] || err "Theme dir not found: $THEME_DIR"
[ -f "$THEME_DIR/layout/theme.liquid" ] || err "No layout/theme.liquid in $THEME_DIR (not a valid theme)"

[ -n "${SHOPIFY_CLI_THEME_TOKEN:-}" ] || err "SHOPIFY_CLI_THEME_TOKEN not set (the shptka_ token from the Theme Access app)"
[ -n "${SHOPIFY_FLAG_STORE:-}" ] || err "SHOPIFY_FLAG_STORE not set (e.g. yourstore.myshopify.com)"

# 1. Ensure Shopify CLI is installed -----------------------------------------
if ! command -v shopify >/dev/null 2>&1; then
  echo "Shopify CLI not found. Installing..."
  if command -v npm >/dev/null 2>&1; then
    npm install -g @shopify/cli@latest
  else
    err "npm not available. Install Node.js 18+ then re-run, or install the CLI manually: https://shopify.dev/docs/themes/tools/cli/install"
  fi
fi
echo "Shopify CLI: $(shopify version)"

# 2. Validate the theme before pushing ---------------------------------------
if [ -f "theme-validator.py" ]; then
  echo "Validating theme structure..."
  python3 theme-validator.py "$THEME_DIR" || echo "WARNING: validator reported issues (continuing)"
fi

# 3. Push --------------------------------------------------------------------
# Theme Access tokens auth non-interactively via the env vars above.
if [ "$PUBLISH" = "--live" ]; then
  echo "Pushing to the LIVE theme on $SHOPIFY_FLAG_STORE ..."
  read -r -p "This OVERWRITES the published theme. Type 'yes' to continue: " ok
  [ "$ok" = "yes" ] || err "Aborted."
  shopify theme push --path="$THEME_DIR" --live --allow-live
else
  echo "Pushing as an unpublished theme to $SHOPIFY_FLAG_STORE ..."
  shopify theme push --path="$THEME_DIR" --unpublished --json
fi

echo "Done. Open the store admin > Online Store > Themes to preview/customize."
