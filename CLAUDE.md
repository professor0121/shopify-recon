# CLAUDE.md

This repo's agent instructions live in [AGENTS.md](AGENTS.md). Read that file.

Quick version:

- Full clone: `python3 shopify-recon.py <store-url> ./output` (theme lands in `./output/theme/`)
- Deploy: set `SHOPIFY_CLI_THEME_TOKEN` and `SHOPIFY_FLAG_STORE`, then `./deploy.sh ./output/theme`
- `deploy.sh` installs the Shopify CLI if it is missing and pushes via a Theme Access token (no OAuth login)
- Never commit secrets; default to `--unpublished`; the clone is a scaffold, not a pixel-perfect copy

See AGENTS.md for the pipeline order (it matters), the deploy steps, and the honest limits.
