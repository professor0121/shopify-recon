#!/bin/bash
# SHOPIFY LIQUID INSPECTOR v3 - Deep Liquid Structure Analysis
# Extract theme metadata, products, collections, AND reverse-engineer Liquid structure
# Kiro | 2026-06-21
# Usage: ./shopify-liquid-inspector.sh <STORE_URL> [output_dir]

set -e

STORE_URL="${1:-}"
OUTPUT_DIR="${2:-./_shopify-liquid}"
DOMAIN=""
TIMEOUT=8

if [ -z "$STORE_URL" ]; then
  echo "Usage: $0 <STORE_URL> [output_dir]"
  echo "   Example: $0 https://www.allbirds.com ./allbirds-extract"
  exit 1
fi

DOMAIN=$(echo "$STORE_URL" | sed 's|https\?://||' | cut -d'/' -f1)

echo "SHOPIFY LIQUID INSPECTOR v3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Store: $DOMAIN"
echo "  Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR/sections" "$OUTPUT_DIR/templates" "$OUTPUT_DIR/api"

# [1] HOMEPAGE HTML + THEME METADATA
echo "[1/6] Extracting theme metadata + homepage structure..."
RAW_THEME=$(timeout $TIMEOUT curl -s "$STORE_URL" -A "Mozilla/5.0" 2>/dev/null)

# Extract theme metadata
echo "$RAW_THEME" | grep -o 'Shopify.theme = {[^}]*}' | sed 's/Shopify.theme = //' > "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "{}" > "$OUTPUT_DIR/theme-metadata.json"
[ -s "$OUTPUT_DIR/theme-metadata.json" ] || echo "{}" > "$OUTPUT_DIR/theme-metadata.json"

# Save full homepage HTML for analysis
echo "$RAW_THEME" > "$OUTPUT_DIR/homepage.html"

if [ -s "$OUTPUT_DIR/theme-metadata.json" ] && [ "$(cat "$OUTPUT_DIR/theme-metadata.json")" != "{}" ]; then
  THEME_NAME=$(jq -r '.name // "Unknown"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "Unknown")
  THEME_ID=$(jq -r '.id // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")
  echo "    Theme: $THEME_NAME (ID: $THEME_ID)"
else
  echo "    Homepage captured"
fi

# [2] DETECT LIQUID TEMPLATES
echo "[2/6] Detecting Liquid template structure..."
echo "$RAW_THEME" | grep -oE 'template-[a-z0-9\-]*' | sort -u > "$OUTPUT_DIR/templates/detected-templates.txt" 2>/dev/null || touch "$OUTPUT_DIR/templates/detected-templates.txt"

# Also look for page-type hints
echo "$RAW_THEME" | grep -oE 'page-type[^"]*|data-template[^"]*' >> "$OUTPUT_DIR/templates/detected-templates.txt" 2>/dev/null || true

TEMPLATE_COUNT=$(wc -l < "$OUTPUT_DIR/templates/detected-templates.txt" 2>/dev/null | tr -d ' ')
echo "    Found $TEMPLATE_COUNT template hints"

# [3] EXTRACT SECTION ARCHITECTURE
echo "[3/6] Analyzing section architecture..."

# Look for data-section-type (indicates custom sections in theme)
echo "$RAW_THEME" | grep -oE 'data-section-type="[^"]*"|data-section-id="[^"]*"' | sort -u > "$OUTPUT_DIR/sections/section-markup.txt" 2>/dev/null || touch "$OUTPUT_DIR/sections/section-markup.txt"

# Extract section IDs for rendering API
echo "$RAW_THEME" | grep -oE 'data-section-id="[^"]*"' | sed 's/data-section-id="\([^"]*\)"/\1/' | sort -u > "$OUTPUT_DIR/sections/section-ids.txt" 2>/dev/null || touch "$OUTPUT_DIR/sections/section-ids.txt"

SECTION_COUNT=$(wc -l < "$OUTPUT_DIR/sections/section-ids.txt" 2>/dev/null | tr -d ' ')
echo "    Detected $SECTION_COUNT sections"

# [4] PRODUCTS API
echo "[4/6] Fetching products catalog..."
timeout $TIMEOUT curl -s "https://$DOMAIN/products.json?limit=250" -A "Mozilla/5.0" 2>/dev/null > "$OUTPUT_DIR/api/products.json" || echo '{"products":[]}' > "$OUTPUT_DIR/api/products.json"

PRODUCT_COUNT=$(jq -r '.products | length' "$OUTPUT_DIR/api/products.json" 2>/dev/null || echo 0)
echo "    Found $PRODUCT_COUNT products"

# [5] COLLECTIONS API
echo "[5/6] Fetching collections..."
timeout $TIMEOUT curl -s "https://$DOMAIN/collections.json" -A "Mozilla/5.0" 2>/dev/null > "$OUTPUT_DIR/api/collections.json" || echo '{"collections":[]}' > "$OUTPUT_DIR/api/collections.json"

COLLECTION_COUNT=$(jq -r '.collections | length' "$OUTPUT_DIR/api/collections.json" 2>/dev/null || echo 0)
echo "    Found $COLLECTION_COUNT collections"

# [6] EXTRACT THEME ASSETS & GENERATE REPORT
echo "[6/6] Extracting theme assets + generating report..."

# Extract all asset URLs
echo "$RAW_THEME" | grep -oE 'cdn\.shopify\.com/s/files/[^"]*\.(css|js)' | sort -u > "$OUTPUT_DIR/asset-urls.txt" 2>/dev/null || touch "$OUTPUT_DIR/asset-urls.txt"
echo "$RAW_THEME" | grep -oE 'shopifycdn\.com/[^"]*\.(css|js)' | sort -u >> "$OUTPUT_DIR/asset-urls.txt" 2>/dev/null || true
sort -u "$OUTPUT_DIR/asset-urls.txt" -o "$OUTPUT_DIR/asset-urls.txt"

ASSET_COUNT=$(wc -l < "$OUTPUT_DIR/asset-urls.txt" 2>/dev/null | tr -d ' ')

# Generate comprehensive report
cat > "$OUTPUT_DIR/LIQUID-ANALYSIS.md" << EOF
# Shopify Liquid Theme Deep Analysis
**Store:** $DOMAIN
**Generated:** $(date)
**Tool:** Shopify Liquid Inspector v3

---

## Theme Information
EOF

if [ -s "$OUTPUT_DIR/theme-metadata.json" ] && [ "$(cat "$OUTPUT_DIR/theme-metadata.json")" != "{}" ]; then
  cat >> "$OUTPUT_DIR/LIQUID-ANALYSIS.md" << EOF
- **Theme Name:** $(jq -r '.name // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")
- **Theme ID:** $(jq -r '.id // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")
- **Theme Role:** $(jq -r '.role // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")
- **Schema Version:** $(jq -r '.schema_version // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")
EOF
fi

cat >> "$OUTPUT_DIR/LIQUID-ANALYSIS.md" << EOF

---

## Store Architecture

### Data Collected
- **Products:** $PRODUCT_COUNT (via /products.json API)
- **Collections:** $COLLECTION_COUNT (via /collections.json API)
- **Detected Sections:** $SECTION_COUNT unique sections
- **Detected Templates:** $TEMPLATE_COUNT template types
- **Theme Assets:** $ASSET_COUNT CSS/JS files

### Shopify APIs Accessible
/products.json - Full product catalog with variants, pricing, images
/collections.json - Collection metadata and structure
/cart.json - Shopping cart API
/search.json - Search API with query parameter

---

## Liquid Template Structure

### Detected Templates
\`\`\`
$(cat "$OUTPUT_DIR/templates/detected-templates.txt" 2>/dev/null | head -20)
\`\`\`

**What this means:**
- Each template file in \`templates/\` folder corresponds to a page type
- \`template-index\` = homepage (\`templates/index.liquid\`)
- \`template-product\` = product page (\`templates/product.liquid\`)
- \`template-collection\` = collection page (\`templates/collection.liquid\`)

---

## Section Architecture

### Sections Detected
- **Total Sections:** $SECTION_COUNT
- **Type:** Likely custom sections or legacy hardcoded sections

### What You Can Learn
1. **Section Organization** - How theme builder sections are structured
2. **Section IDs** - Unique identifiers for each rendered section block
3. **Layout Pattern** - Homepage section arrangement and ordering

### Section Markup Hints
\`\`\`
$(cat "$OUTPUT_DIR/sections/section-markup.txt" 2>/dev/null | head -10)
\`\`\`

---

## API Endpoints Available

### 1. Products API
**Endpoint:** \`/products.json?limit=250&page=N\`
**Returns:** Full product catalog with:
- Product titles, descriptions, handles
- Variants with SKUs, pricing, weight, availability
- Product images and featured images
- Collections membership
- Product tags and metadata
- Vendor information

**Usage:**
\`\`\`bash
curl -s "https://$DOMAIN/products.json?limit=250" | jq '.products[] | {title, handle, price: .variants[0].price}'
\`\`\`

### 2. Collections API
**Endpoint:** \`/collections.json\`
**Returns:**
- Collection titles and handles
- Collection descriptions and images
- Product counts

**Usage:**
\`\`\`bash
curl -s "https://$DOMAIN/collections.json" | jq '.collections[] | {title, handle}'
\`\`\`

### 3. Search API
**Endpoint:** \`/search.json?q=QUERY\`
**Returns:** Products matching search query

### 4. Cart API
**Endpoint:** \`/cart.json\`
**Returns:** Current cart contents (public info)

---

## Theme Asset Analysis

### CSS/JavaScript URLs Found
\`\`\`
$(head -20 "$OUTPUT_DIR/asset-urls.txt" 2>/dev/null || echo "No assets found")
\`\`\`

### What You Can Extract
From these assets, analyze:
- Feature implementation logic
- Frontend interactivity (event handlers, AJAX calls)
- Component dependencies and imports
- API endpoint patterns
- Tracking and analytics code

---

## Reverse Engineering Possibilities

### 1. Clone Product Structure
**Use:** \`/products.json\` API data
**Extract:** Product metadata, images, pricing logic
**Create:** Product pages matching structure

### 2. Replicate Layout
**Use:** HTML structure + section ordering
**Extract:** CSS styles from theme assets
**Build:** Homepage layout matches

### 3. Copy Features
**Use:** JavaScript asset analysis
**Extract:** Feature implementation patterns
**Adapt:** Logic to your own theme

### 4. Understand Theme Architecture
**Use:** Template detection + section analysis
**Extract:** Theme's file structure blueprint
**Learn:** Best practices from established themes

---

## Important Limitations

**Cannot Access:**
- Original \`.liquid\` template source files (compiled server-side)
- Section schema definitions (\`schema.json\` blocks)
- Theme \`config.json\` structure
- Snippet code (unless inlined in HTML/JS)
- Admin-only theme settings

**Can Access:**
- Compiled HTML output
- Public API endpoints
- Theme CSS/JS assets
- Product and collection data
- Metadata and structure hints

---

## Ethical Guidelines

This data is **publicly accessible** via:
- Browser inspection (HTML, CSS, JS)
- Public Shopify API endpoints
- CDN-served assets

**Do's:**
- Competitive analysis and research
- Learning theme architecture
- Reverse-engineering features for inspiration
- Building your own original theme

**Don'ts:**
- Copying theme code wholesale for resale
- Scraping and republishing others' data
- Launching rapid API requests (DDoS-like behavior)
- Violating robots.txt or terms of service

---

## Quick Command Reference

### View Theme Info
\`\`\`bash
jq . $OUTPUT_DIR/theme-metadata.json
\`\`\`

### Count Total Products
\`\`\`bash
jq '.products | length' $OUTPUT_DIR/api/products.json
\`\`\`

### List Product Titles & Prices
\`\`\`bash
jq '.products[] | {title, price: .variants[0].price}' $OUTPUT_DIR/api/products.json | head -10
\`\`\`

### View Collections
\`\`\`bash
jq '.collections[] | {title, handle, product_count}' $OUTPUT_DIR/api/collections.json
\`\`\`

### Export Product Data to CSV
\`\`\`bash
jq -r '.products[] | [.title, .handle, .variants[0].price] | @csv' $OUTPUT_DIR/api/products.json > products.csv
\`\`\`

### Download First 5 Theme CSS Files
\`\`\`bash
head -5 $OUTPUT_DIR/asset-urls.txt | while read url; do
  echo "Downloading: \$url"
  curl -s "https:\$url" -o "$OUTPUT_DIR/assets/\$(basename \$url)"
done
\`\`\`

### Analyze Theme JavaScript
\`\`\`bash
# Download theme JS for analysis
curl -s "https:\$(head -1 $OUTPUT_DIR/asset-urls.txt | grep '.js')" | head -100
\`\`\`

---

## File Structure

\`\`\`
$OUTPUT_DIR/
├── theme-metadata.json          # Shopify.theme object
├── homepage.html                # Full HTML homepage (for manual inspection)
├── LIQUID-ANALYSIS.md           # This report
│
├── api/
│   ├── products.json            # 250 products with full metadata
│   └── collections.json         # All collections
│
├── templates/
│   └── detected-templates.txt   # Template type hints
│
├── sections/
│   ├── section-ids.txt          # Section IDs (for rendering API)
│   └── section-markup.txt       # Raw markup hints
│
└── asset-urls.txt               # Theme CSS/JS URLs
\`\`\`

---

## Next Steps

1. **Explore Products** Analyze product structure and pricing model
2. **Study Collections** Understand categorization strategy
3. **Inspect Assets** Download CSS/JS and reverse-engineer features
4. **Manual Inspection** Open \`homepage.html\` in browser DevTools
5. **Build Your Theme** Use insights to create your own version

---

Generated by **Shopify Liquid Inspector v3** | Kiro | 2026-06-21
EOF

echo "    Deep analysis report generated"

echo ""
echo "LIQUID ANALYSIS COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Output: $OUTPUT_DIR"
echo ""
echo "Summary:"
echo "   • Theme: $(jq -r '.name // "N/A"' "$OUTPUT_DIR/theme-metadata.json" 2>/dev/null || echo "N/A")"
echo "   • Products: $PRODUCT_COUNT"
echo "   • Collections: $COLLECTION_COUNT"
echo "   • Sections: $SECTION_COUNT"
echo "   • Templates: $TEMPLATE_COUNT"
echo "   • Assets: $ASSET_COUNT CSS/JS files"
echo ""
echo "Reports:"
echo "   • $OUTPUT_DIR/LIQUID-ANALYSIS.md - Full deep analysis"
echo "   • $OUTPUT_DIR/homepage.html - Raw homepage HTML"
echo ""
echo "Data:"
echo "   • $OUTPUT_DIR/api/products.json - $PRODUCT_COUNT products"
echo "   • $OUTPUT_DIR/api/collections.json - $COLLECTION_COUNT collections"
echo "   • $OUTPUT_DIR/asset-urls.txt - $ASSET_COUNT theme assets"
echo ""
echo "Start Here:"
echo "   cat $OUTPUT_DIR/LIQUID-ANALYSIS.md"
echo "   jq '.products[0]' $OUTPUT_DIR/api/products.json"
echo "   open $OUTPUT_DIR/homepage.html"
