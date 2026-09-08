# Shopify Recon

Point it at a Shopify store and it tells you what theme they run, how the
design system is put together, how the cart works, and what apps are bolted on.
Then it can rebuild the whole thing as an editable Liquid theme. Think of it as
BuiltWith for Shopify, except it also hands you the code.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Here is what it pulls out of a store:

- Theme DNA, so you know if they are on Dawn, Turbo, Prestige, Motion or a custom build
- The design system: colors, fonts, CSS variables, spacing, breakpoints
- Cart and checkout flow, including AJAX endpoints and payment methods
- Product data: pricing tiers, the full variant matrix, metafields, inventory
- JavaScript logic like cart handlers, variant selectors, and which third-party apps are loaded
- An SEO pass (meta tags, Open Graph, JSON-LD, heading structure, a score out of 100)
- A performance pass (page weight, render-blocking resources, image optimization)
- Side-by-side comparison across several stores at once
- Reconstructed Liquid sections built from the rendered HTML
- A deep Liquid extractor that uses five public vectors: the Section Rendering API, leaked section settings, the Shopify.theme object, the Storefront GraphQL API, and template section mapping

## Quick Start

```bash
# Clone
git clone https://github.com/krickelsync/shopify-recon.git
cd shopify-recon
pip install -r requirements.txt

# Prove it works first (offline, takes seconds)
./verify.sh

# Preview the pipeline without running it (no network calls)
python3 shopify-recon.py https://rothys.com --dry-run

# Full clone (extract + analyze + generate editable theme)
python3 shopify-recon.py https://rothys.com ./rothys-clone

# Compare multiple competitors
python3 multi-store-comparator.py allbirds.com rothys.com taylorstitch.com
```

`./verify.sh` is the fastest way to confirm a fresh checkout is healthy: it
checks dependencies, parses every tool, and dry-runs the full pipeline without
touching the network. Add `--golden` for a real clone diffed against a stored
fixture.

## What It Looks Like

```
╔═══════════════════════════════════════════════════════════════╗
║  SHOPIFY RECON - Store Intelligence Report                  ║
╠═══════════════════════════════════════════════════════════════╣
║  Store: rothys.com                                          ║
╚═══════════════════════════════════════════════════════════════╝

╭────────────────────────── Theme DNA ───────────────────────╮
│  Detected Theme     Prestige (custom build)                │
│  Developer          Maestrooo                               │
│  Price              $340                                    │
│  Custom Build       Yes                                    │
│  Customization      Heavy Customization (7 custom sections) │
│  Confidence         [███░░░░░░░] 30%                       │
│  Schema Name        DNA                                    │
│  Schema Version     26.06.17                               │
│  Sections           10                                     │
╰───────────────────────────────────────────────────────────────╯

╭────────────────────────── Tech Stack ──────────────────────╮
│  jQuery                                                    │
│  Tailwind CSS                                              │
│  Shopify (native)                                          │
╰───────────────────────────────────────────────────────────────╯

╭────────────────────── Store Statistics ────────────────────╮
│  Products           250                                    │
│  Collections        30                                     │
│  Total Variants     3650                                   │
│  Avg Price          $122.77                                │
│  Availability       83.1%                                 │
╰───────────────────────────────────────────────────────────────╯

╭────────────────── Cart & Checkout Flow ───────────────────╮
│  Cart Type          drawer, modal                          │
│  Payments           Stripe, PayPal, Apple Pay              │
│  Express Checkout   Yes                                 │
│  Variant Selector   button                                 │
╰───────────────────────────────────────────────────────────────╯

╭────────────────── Third-Party Apps ──────────────────────╮
│  ╭────────────────┬────────────╮                              │
│  │ App            │ References │                              │
│  ├────────────────┼────────────┤                              │
│  │ swym_wishlist  │        418 │                              │
│  │ constructor_io │         69 │                              │
│  │ fontawesome    │         56 │                              │
│  │ yotpo          │          2 │                              │
│  ╰────────────────┴────────────╯                              │
╰───────────────────────────────────────────────────────────────╯
```

## Features

### Theme DNA Fingerprint

Detect which Shopify theme any store is using:

```bash
python3 theme-dna.py --url=https://rothys.com
```

- Identifies 15+ popular themes (Dawn, Turbo, Prestige, Motion, Impulse, Empire, etc.)
- Detects custom builds and in-house themes
- Estimates customization level (light heavy)
- Extracts schema name, version, and theme store ID
- Confidence scoring with evidence

### CSS/Style Cloner

Extract a store's complete design system:

```bash
python3 css-style-cloner.py ./store-data ./output
```

- Extracts all colors (hex, rgb, named) with categorization
- Identifies font families, sizes, weights
- Extracts CSS variables and custom properties
- Detects responsive breakpoints
- Generates `theme.css` and `settings_schema.json`

### Section Reverse-Engineer

Reconstruct Liquid section files from rendered HTML:

```bash
python3 section-reverse-engineer.py ./store-data ./output
```

- Detects `shopify-section-*` patterns in HTML
- Extracts section settings (images, headings, links, colors)
- Generates valid `.liquid` files with `{% schema %}` blocks
- Handles: banner, product_carousel, spacer, quick_links, flexible, etc.

### Cart & Checkout Flow Mapper

Trace the complete e-commerce flow:

```bash
python3 cart-flow-mapper.py ./store-data ./output
```

- Detects cart endpoints (/cart/add.js, /cart/change.js, etc.)
- Identifies cart type (drawer, page, modal, AJAX)
- Detects payment methods (Stripe, PayPal, Apple Pay, Shop Pay)
- Generates Mermaid flow diagram
- Traces checkout flow and express checkout buttons

### Product Schema Analyzer

Deep product intelligence:

```bash
python3 product-schema-analyzer.py ./store-data ./output
```

- Pricing strategy analysis (tiers, discounts, ranges)
- Variant matrix builder (option combinations)
- Metafield extraction from tags
- Inventory status and availability
- SKU format detection

### JS Logic Extractor

Extract and map theme JavaScript:

```bash
python3 js-logic-extractor.py ./store-data ./output
```

- Extracts all function definitions
- Detects cart logic (add, update, render handlers)
- Extracts `selectCallback` (variant selection handler)
- Maps JS variables to Shopify Liquid objects
- Detects third-party apps (Swym, Klaviyo, Yotpo, etc.)

### SEO X-Ray

Complete SEO analysis:

```bash
python3 seo-xray.py --url=https://rothys.com
```

- Meta tags, Open Graph, Twitter Cards
- JSON-LD structured data
- Heading hierarchy (H1-H6)
- Internal/external link analysis
- Image alt text audit
- Canonical URLs and hreflang
- Overall SEO score (0-100)

### Performance Profiler

Page speed and optimization analysis:

```bash
python3 perf-profiler.py --url=https://rothys.com
```

- Page weight breakdown (HTML, CSS, JS)
- Script loading strategy (async, defer, render-blocking)
- Image optimization (lazy loading, WebP, responsive)
- Font loading analysis
- Performance score (0-100) with recommendations

### Multi-Store Comparator

Side-by-side competitive analysis:

```bash
python3 multi-store-comparator.py allbirds.com rothys.com taylorstitch.com
```

- Batch extract from multiple stores
- Side-by-side metrics table
- CSV export for spreadsheets
- Competitive rankings (most products, best availability, etc.)

## Full Clone Pipeline

One command does everything:

```bash
./shopify-clone-master.sh clone https://rothys.com ./rothys-clone
```

Generates:
```
rothys-clone/
├── extracted/ - Raw data (products, collections, HTML, metadata)
├── analysis/
│   ├── sections/ - Reconstructed .liquid section files
│   ├── styles/ - theme.css, settings_schema.json
│   ├── js-logic/ - Functions, cart logic, selectCallback
│   ├── cart-flow/ - Flow diagram, payment methods
│   └── products/ - Pricing intelligence, variant matrix
├── theme/ - Production-ready Shopify Liquid theme
└── website/ - Standalone HTML website clone
```

## Deploy to a store

Once you have a theme in `./output/theme/`, push it with `deploy.sh`. It
installs the Shopify CLI if it is missing and authenticates with a Theme Access
token, so there is no interactive login. AI agents (Claude Code, Cursor, etc.)
can run this step too; see AGENTS.md.

Get a token: in Shopify admin, install the free Theme Access app, add a user,
and it emails a password starting with `shptka_`. That password is the token.

```bash
export SHOPIFY_CLI_THEME_TOKEN=your_shptka_token
export SHOPIFY_FLAG_STORE=yourstore.myshopify.com

./deploy.sh ./output/theme          # push as an unpublished theme
./deploy.sh ./output/theme --live   # publish to live (prompts to confirm)
```

Do not commit the token. It is gitignored by default.

## Requirements

```
Python 3.8+
rich (for TUI dashboard)
jq (for JSON processing)
curl
```

```bash
pip install rich
```

## Command Reference

| Command | Description |
|---------|-------------|
| `./shopify-clone-master.sh extract <url> <output>` | Extract data from store |
| `./shopify-clone-master.sh analyze <input> <output>` | Run all 6 analyzers |
| `./shopify-clone-master.sh clone <url> <output>` | Full clone (extract + analyze + generate) |
| `./shopify-clone-master.sh compare <store1> <store2>` | Compare stores side-by-side |
| `./shopify-clone-master.sh theme <input> <output>` | Generate Liquid theme |
| `./shopify-clone-master.sh web <input> <output>` | Generate HTML website |
| `python3 theme-dna.py --url=<url>` | Theme fingerprint |
| `python3 seo-xray.py --url=<url>` | SEO analysis |
| `python3 perf-profiler.py --url=<url>` | Performance profile |

## Honest Limitations

- **.liquid source files** cannot be extracted (compiled server-side). We reconstruct from rendered HTML.
- **External JS bundles** may be blocked by CloudFront. We extract inline scripts.
- **Theme clone** is a scaffold - valid structure but needs manual styling.
- **Images** are URL references only (CDN may block downloads).
- **Theme detection** is heuristic - confidence varies by store customization.

## Contributing

If you want to help, the most useful things are adding theme fingerprints to
`theme-dna.py`, improving the section reconstruction patterns, writing new
analyzer modules, or just running it against more stores and filing what breaks.

## License

MIT. See the [LICENSE](LICENSE) file.

Built by krickel.
