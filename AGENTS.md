# AGENTS.md

Instructions for AI agents (Claude Code, Cursor, Codex, etc.) working in this
repo. Read this before running anything. A human-readable overview is in
README.md; this file is the operational guide.

## What this repo does

Shopify Recon clones a Shopify store into an editable Liquid theme. You give it
a URL, it extracts the store's data and structure, rebuilds it as a Shopify
theme whose sections a buyer can customize in the theme editor, then deploys it
to a store over the Shopify CLI.

It only uses public endpoints. It does not bypass auth or scrape anything behind
a login.

## First thing: prove it works (`./verify.sh`)

Before you read every tool or trust this doc, run the self-test:

```bash
pip install -r requirements.txt
./verify.sh            # phases 1-3: deps, syntax, dry-run plan (OFFLINE, seconds)
./verify.sh --golden   # phase 4: real clone of a test store, diffed vs a golden fixture
```

`./verify.sh` makes zero network calls and confirms: all dependencies import,
every Python tool parses, and the full pipeline plans its steps. Green `ALL
CHECKS PASSED` and exit 0 means the repo is wired up correctly. `--golden` does
a real clone and checks the output structure has not regressed against
`tests/golden/rothys.json`.

To preview the pipeline without running it:

```bash
python3 shopify-recon.py https://example-store.com --dry-run
```

This prints all steps and the exact command each would run, touching nothing.

## The pipeline (run order matters)

`shopify-recon.py` runs the whole thing in 27 steps. The last four are the ones
that make the theme editable, and their order is load-bearing:

1. `section-detector.py` - finds the REAL sections on each page from the
   `shopify-section-*` markers in the rendered HTML, and extracts each section's
   actual inner markup. Pages with markers are trusted exactly; non-Shopify
   sources fall back to structural detection. It never invents sections the
   source page does not have.
2. `json-template-builder.py` - turns each static `.liquid` template into a JSON
   template so sections become reorderable/addable/removable in the editor. It
   reads the detector output, so the templates match the real page 1:1.
3. `block-ifier.py` - gives each section blocks, presets, and
   `shopify_attributes` so elements are draggable. Sections carrying real cloned
   markup or commerce logic are PRESERVED (additive blocks only), never rebuilt.
4. `theme-validator.py` - checks structure and reports an Editor-Readiness Score.

Do not reorder these. If you block-ify before building JSON templates, the
sections the builder creates never get blocks and the score drops.

## How to run a full clone

```bash
pip install -r requirements.txt
python3 shopify-recon.py https://example-store.com ./output
```

Output lands in `./output/theme/` as a deployable Shopify theme.

## How to deploy (Shopify CLI + Theme Access)

Use `deploy.sh`. It installs the Shopify CLI if it is missing and pushes with a
Theme Access token, so there is no interactive OAuth step.

```bash
export SHOPIFY_CLI_THEME_TOKEN=shptka_xxxxxxxx   # from the Theme Access app
export SHOPIFY_FLAG_STORE=yourstore.myshopify.com
./deploy.sh ./output/theme            # pushes as an unpublished theme
./deploy.sh ./output/theme --live     # publishes to live (prompts to confirm)
```

To get the token: in Shopify admin, install the free "Theme Access" app, add a
user, and it emails a password starting with `shptka_`. That password is the
token. Never commit it.

## Rules for agents

- Never commit secrets. `SHOPIFY_CLI_THEME_TOKEN`, `.env`, and credential files
  are gitignored. Keep them in env vars.
- Default to `--unpublished`. Only push `--live` when the user explicitly asks,
  and the script will still confirm.
- The cloned theme is a scaffold with real structure and content, not a
  pixel-perfect copy. Styling and images still need work. Say so honestly.
- You cannot extract the original `.liquid` source from a competitor store. It
  is compiled server-side. This toolkit rebuilds from rendered output. Do not
  claim otherwise.
- After changing a tool, re-run it on a test store before saying it works.
- `auto-sync.sh` commits and pushes this repo to GitHub. Run it after changes.

## Honest limits

- Original `.liquid` source: not extractable (server-compiled).
- External JS bundles: may be blocked by CDN; inline scripts are extracted.
- Images: stored as URL references; CDNs often block bulk download.
- Theme detection: heuristic, confidence varies by how custom the store is.
