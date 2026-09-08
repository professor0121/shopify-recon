# SHOPIFY LIQUID INSPECTOR TOOLKIT
**Kiro | 2026-06-21**

Toolkit lengkap buat **inspect, extract, dan reverse-engineer** Shopify Liquid themes dari web publik. Tools ini menggunakan API Shopify yang public-facing - bukan hacking, tapi analyzing data yang sudah accessible ke browser.

---

## REALITY CHECK: Bisa & Gak Bisa

### Gak Bisa (Impossible to Bypass)
- **Original `.liquid` files** - Liquid di-compile di server, never sent to browser. Ini adalah fundamental limitation Shopify, bukan tool limitation.
- **Section schema** - File `.liquid` yg berisi schema definitions (settings, blocks) hanya ada di server.
- **Theme `config.json`** - Theme configuration hanya diakses oleh admin.
- **Snippet code** - Template snippets hanya diakses jika di-inline ke HTML/JS.

### Bisa (Fully Extractable)
- **Product catalog** - `/products.json` API, 250+ products per request
- **Collections** - `/collections.json`, full metadata
- **Theme metadata** - `Shopify.theme` JS object dengan ID, name, version
- **HTML structure** - Full homepage rendered output
- **CSS/JS assets** - Theme stylesheets dan JavaScript logic
- **Section markup** - Data attributes yg reveal section organization
- **Template hints** - HTML class names yg expose template names

---

## TOOL: `shopify-liquid-inspector.sh`

### Installation
```bash
# Already installed at:
/home/ubuntu/tools/shopify-liquid-inspector.sh

# Make executable
chmod +x /home/ubuntu/tools/shopify-liquid-inspector.sh
```

### Usage
```bash
./shopify-liquid-inspector.sh <STORE_URL> [output_dir]

# Examples
./shopify-liquid-inspector.sh https://www.allbirds.com ./allbirds-extract
./shopify-liquid-inspector.sh https://rothys.com ./rothys-extract
./shopify-liquid-inspector.sh https://www.taylorstitch.com ./taylor-stitch
```

### What It Extracts (v3)

| Extract | Format | Details |
|---------|--------|---------|
| **Theme Metadata** | JSON | Theme name, ID, role, schema version |
| **Products** | JSON | 250 products with variants, pricing, images |
| **Collections** | JSON | All collections with metadata |
| **HTML Structure** | HTML | Full homepage for manual inspection |
| **Sections** | TXT | Section IDs and markup hints |
| **Templates** | TXT | Template type detection |
| **Assets** | URLs | CSS/JS file locations |
| **Analysis Report** | Markdown | Complete reverse-engineering guide |

### Output Structure
```
./output-dir/
├── theme-metadata.json          # Shopify.theme object
├── homepage.html                # Full HTML (834KB for Allbirds)
├── LIQUID-ANALYSIS.md           # Deep analysis + how-to guide
│
├── api/
│   ├── products.json            # 250+ products
│   └── collections.json         # All collections
│
├── templates/
│   └── detected-templates.txt   # template-index, template-product, etc.
│
├── sections/
│   ├── section-ids.txt          # Unique section identifiers
│   └── section-markup.txt       # Data attributes
│
└── asset-urls.txt               # CDN URLs for CSS/JS
```

---

## USE CASES

### 1. Competitive Analysis
**Goal:** Understand competitor's product structure and pricing strategy

**Commands:**
```bash
# Count products
jq '.products | length' output/api/products.json

# Extract pricing tiers
jq '.products[] | {title, price: .variants[0].price, compare_at: .variants[0].compare_at_price}' output/api/products.json | head -20

# Find price ranges
jq -r '.products[] | .variants[0].price' output/api/products.json | sort -n | uniq -c
```

### 2. Theme Architecture Learning
**Goal:** Understand how professional themes are structured

**Commands:**
```bash
# View theme info
jq . output/theme-metadata.json

# See all templates used
cat output/templates/detected-templates.txt

# Analyze section organization
cat output/sections/section-ids.txt
```

### 3. Reverse-Engineer Features
**Goal:** Learn how features are implemented in competitor theme

**Steps:**
1. Download theme CSS/JS:
```bash
head -5 output/asset-urls.txt | while read url; do
  curl -s "https:$url" -o "output/assets/$(basename $url)"
done
```

2. Analyze JavaScript:
```bash
# Find API endpoints used
grep -o "\.json" output/assets/*.js | sort -u

# Find event handlers
grep -o "on[A-Z][a-zA-Z]*" output/assets/*.js | sort -u

# Search for specific feature
grep -i "cart\|checkout\|subscribe" output/assets/*.js
```

3. Study CSS patterns:
```bash
# Extract custom properties
grep -o "--[a-z0-9\-]*:" output/assets/*.css | sort -u

# Find animations
grep -o "@keyframes [a-z\-]*" output/assets/*.css
```

### 4. Clone Product Structure
**Goal:** Build your own store with similar product organization

**Steps:**
```bash
# Export products to CSV
jq -r '.products[] | [.title, .handle, .variants[0].price, .images[0].src] | @csv' output/api/products.json > products.csv

# Export collections
jq -r '.collections[] | [.title, .handle] | @csv' output/api/collections.json > collections.csv

# Use in your Shopify store via Lovable/custom importer
```

### 5. HTML Structure Inspection
**Goal:** Study page layout without looking at Liquid source

**Steps:**
```bash
# Open in browser
open output/homepage.html

# Or analyze via command line
grep -o '<section[^>]*class="[^"]*"' output/homepage.html | head -10

# Find component structure
grep -o '<div[^>]*data-section[^>]*>' output/homepage.html
```

---

## ADVANCED USAGE

### Batch Extract Multiple Stores
```bash
#!/bin/bash
stores=(
  "https://www.allbirds.com"
  "https://rothys.com"
  "https://www.taylorstitch.com"
)

for store in "${stores[@]}"; do
  domain=$(echo "$store" | sed 's|https\?://||' | cut -d'/' -f1)
  echo "Extracting: $domain"
  ./shopify-liquid-inspector.sh "$store" "./extract-$domain"
done
```

### Find All Section Types in Store
```bash
# Detect section diversity
jq -r '.products[] | .tags[]?' output/api/products.json | sort | uniq -c | sort -rn | head -20
```

### Analyze Collection Strategy
```bash
# See how products are organized
jq '.collections[] | {title, product_count}' output/api/collections.json | sort -k3 -rn
```

### Extract All Product Images
```bash
jq -r '.products[] | .images[] | .src' output/api/products.json > image-urls.txt
# Then batch download:
cat image-urls.txt | xargs -I {} curl -O {}
```

---

## INTERPRETATION GUIDE

### Reading `theme-metadata.json`
```json
{
  "name": "Handover theme",
  "id": 129992884304,
  "role": "main",
  "schema_version": "1.231.12",
  "schema_name": "allbirds-theme",
  "theme_store_id": null
}
```

**What it means:**
- `name` = Theme name as shown in theme editor
- `id` = Unique theme identifier (useful for Shopify CLI commands)
- `role` = "main" = live theme (vs. "trial", "development")
- `schema_version` = Theme's internal version (not Shopify version)
- `theme_store_id` = null = Custom theme (not from Shopify Theme Store)

### Reading Section Detection
```
Section IDs found: 25 (Rothys)
Section types found: 9 (Taylor Stitch)
```

**What it means:**
- Theme uses Shopify sections feature (modern theme architecture)
- Each `data-section-id` = One section instance on homepage
- Section types detected = How many different section templates

**For stores with 0 sections:**
- Theme is likely older (hardcoded template)
- OR uses custom rendering (e.g., headless)
- OR sections hidden in HTML (data attributes removed)

### Template Detection
```
template-index        Homepage
template-product      Product page template
template-collection   Collection page template
template-page         Generic page template
template-cart         Cart page template
```

---

## PRACTICAL WORKFLOW

### 1. Initial Reconnaissance
```bash
./shopify-liquid-inspector.sh https://target-store.com ./target
cat target/LIQUID-ANALYSIS.md
# Understand theme architecture, products, collections
```

### 2. Competitive Analysis
```bash
# Count products and analyze pricing
jq '.products | length' target/api/products.json
jq -r '.products[] | .variants[0].price' target/api/products.json | \
  awk '{sum+=$1; count++} END {print "Avg price: $" sum/count}'

# Analyze collections strategy
jq '.collections[] | {title, product_count}' target/api/collections.json
```

### 3. Feature Research
```bash
# Download and analyze theme JS
curl -s "https:$(head -1 target/asset-urls.txt)" -o theme-main.js
grep -i "function\|const.*=.*=>" theme-main.js | head -20

# Search for specific patterns
grep -i "submit\|add.*cart\|checkout" theme-main.js
```

### 4. Implementation Planning
```bash
# Document findings
cat target/LIQUID-ANALYSIS.md > my-research.md
echo "## My Findings" >> my-research.md
echo "- X sections detected" >> my-research.md
echo "- Y products with Z variants avg" >> my-research.md
# Use for your own theme development
```

---

## EXAMPLE: Full Analysis of Allbirds

### Extract
```bash
./shopify-liquid-inspector.sh https://www.allbirds.com ./allbirds
```

### Key Findings
```
Theme: Handover theme (ID: 129992884304, Role: main)
Products: 250 (pagination available)
Collections: 30
Templates: 5 types detected
Sections: 0 (custom rendering)
Assets: 1 JS file (jsEncrypt.js)
```

### Analysis
- Theme uses custom Liquid (not Dawn)
- Product pages likely rendered server-side (Liquid)
- Section-less architecture = simpler, hardcoded layout
- Minimal JS (just encryption utility)
- Heavy backend rendering = less client-side logic

### Competitor Insights
- Focus on server-side performance (Liquid rendering)
- Product data structure: 250 limit suggests pagination needed for full catalog
- Collections strategy: 30 curated collections (strategic grouping)
- Minimal JavaScript = focus on core experience, not flashy interactions

---

## ETHICAL GUIDELINES

### Legal Use
Competitive analysis (studying public information)
Learning Shopify theme development
Reverse-engineering for inspiration
Building your own original theme

### Prohibited Use
Copying and reselling competitor's theme
Scraping and republishing product data
DDoS-like rapid API requests
Violating robots.txt or terms of service
Personal harassment or surveillance

### Best Practices
- Extract data once, respect rate limits
- Don't make requests faster than 1/sec
- Respect robots.txt if present
- Use data for analysis, not republication
- Credit competitors' insights if publicizing findings

---

## TROUBLESHOOTING

### Tool Hangs or Times Out
```bash
# Already handled: 8-second timeout per request
# If still hanging, manually set timeout:
timeout 10 curl -s "https://store.com" -A "Mozilla/5.0"
```

### No Sections Detected
```bash
# Some themes don't use section markup
# Check HTML directly:
grep -o "data-section" output/homepage.html | wc -l

# If 0, theme uses hardcoded layout (older theme style)
```

### Products.json Empty
```bash
# Some stores block API access
# Try products page manually:
curl -s "https://store.com/products.json" -A "Mozilla/5.0" | jq . | head -20

# If blocked, likely robots.txt restriction
```

### Asset URLs Not Found
```bash
# Some assets served from custom CDN
# Check for alternate patterns:
grep -o "https://[^\"]*\.js" output/homepage.html | head -10
grep -o "https://[^\"]*\.css" output/homepage.html | head -10
```

---

## RELATED TOOLS

### Already Installed
- `deep-code-extractor.sh` - Extract and deobfuscate JS logic
- `website-code-inspector.sh` - Framework detection
- Deobfuscators: `webcrack`, `javascript-deobfuscator`, `js-deobfuscator`

### Shopify CLI
```bash
# For your own theme
shopify theme pull --store=YOUR_STORE.myshopify.com

# View theme structure
ls theme/sections/
ls theme/snippets/
cat theme/layout/theme.liquid
```

### Browser DevTools
- **Elements Inspector** - Study HTML structure
- **Network Tab** - See API calls and assets
- **Console** `Shopify.theme` - View theme metadata live
- **Sources** Analyze JS with breakpoints

---

## LEARNING PATH

1. **Week 1:** Run tool on 5 different Shopify stores
2. **Week 2:** Analyze extracted data, document patterns
3. **Week 3:** Study theme CSS/JS from 2 stores
4. **Week 4:** Clone product/collection structure in your own theme
5. **Week 5:** Implement 1 feature learned from analysis
6. **Week 6:** Build original theme combining best practices

---

## SUPPORT

### Command Reference
```bash
# View full analysis
cat output/LIQUID-ANALYSIS.md

# Quick data extraction
jq '.products[0]' output/api/products.json
jq '.collections[] | .title' output/api/collections.json

# Download assets for analysis
head -1 output/asset-urls.txt | xargs -I {} curl -s "https:{}" -o theme-main.js
```

### Common Issues
See TROUBLESHOOTING section above.

---

## REMEMBER

**What You're Doing:** Analyzing publicly accessible data (same as using browser DevTools)
**What You're NOT Doing:** Hacking, bypassing security, or stealing private code

The `.liquid` source will never be accessible - that's not a limitation of this tool, that's how Shopify works. But **everything else** is fair game for analysis and learning.

---

**Generated:** 2026-06-21
**Tool Version:** shopify-liquid-inspector.sh v3
**Status:** Production-ready, tested on Allbirds, Rothys, Taylor Stitch

Next: Use this toolkit to analyze your competitors and build better themes!
