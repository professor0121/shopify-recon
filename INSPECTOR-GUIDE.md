# Website Code Inspector & Extractor - Usage Guide
**Kiro Shopify Master | 2026-06-21**

Gw udah bikin tool yang bisa:
1. **Detect framework** - Shopify? React? Vue? TypeScript?
2. **Extract semua code** - HTML, CSS, JavaScript
3. **Grab Liquid** - Kalau itu Shopify theme
4. **Analyze struktur** - Tech report + JSON output

---

## Installation & Setup

Tool udah ada di: `/home/ubuntu/tools/website-code-inspector.sh`

**Executable:** Ready
**Requirements:** curl, grep, bash (semua standard Linux)

---

## Usage

```bash
./website-code-inspector.sh <URL> [output_dir]
```

### Examples

**Example 1: Shopify Store (Gymshark)**
```bash
/home/ubuntu/tools/website-code-inspector.sh https://www.gymshark.com ./gymshark-extract
```

Output:
```
Inspecting: https://www.gymshark.com
Output: ./gymshark-extract

[1/7] Fetching HTML + Headers...
Headers saved

[2/7] Detecting framework & language...
SHOPIFY THEME DETECTED
Framework: Shopify Liquid
 React/Next.js detected
JavaScript <script> tags: 4
CSS references: 2
LIQUID CODE FOUND:
{{amount}}
{{discount}}
... (29 Liquid variables)
```

**Example 2: Custom React Site**
```bash
/home/ubuntu/tools/website-code-inspector.sh https://example.com ./example-extract
```

**Example 3: Lovable Project**
```bash
/home/ubuntu/tools/website-code-inspector.sh https://yourlovablesite.vercel.app ./lovable-extract
```

---

## Output Files

```
output_dir/
├── source.html              # Full HTML source
├── headers.txt              # HTTP headers (server, content-type, etc.)
├── tech-report.txt          # Framework detection report
├── analysis.json            # Structured analysis (JSON)
├── extracted-liquid.liquid  # Liquid code (if Shopify)
├── theme-structure.html     # Theme HTML structure
├── css/
│   ├── inline.css           # Inline <style> blocks
│   └── external.css         # Downloaded external CSS
└── js/
    ├── inline.js            # Inline <script> code
    └── external.js          # Downloaded external JS
```

---

## What Gets Detected

### Frameworks
| Signal | What It Means |
|--------|---------------|
| `Shopify` + `/cdn/shop` + `window.Shopify` | **Shopify Liquid Theme** |
| `data-react-root` + `__next` | **React/Next.js** |
| `data-v-app` | **Vue.js** |
| `.vercel.com` + `.tsx/.ts` | **Lovable (React-based)** |
| `module` type scripts | **TypeScript** |

### Code Extracted
- **HTML:** Full page structure
- **CSS:** Inline + external stylesheets
- **JavaScript:** Behavior code (analytics/trackers removed)
- **Liquid:** Shopify template variables (if applicable)

### What Gets Dropped
- Google Analytics (gtag, ga.)
- Ad networks (ads.js, adsbygoogle)
- Social trackers (Facebook pixel, hotjar)
- Shopify buttons (PayPal, checkout)
- Intercom/Zendesk chat

---

## Next Steps After Extraction

### If Shopify Theme Detected
**Use `shopify-theme-conversion` skill:**
```bash
# Convert extracted Liquid to standalone theme
hermes skill load shopify-theme-conversion
# Then gw akan: port pure Liquid deployable theme
```

### If React/Lovable Detected
**Use `shopify-theme-conversion` skill:**
```bash
# Port React components to Shopify Liquid
# Components extracted Liquid sections/templates
```

### If Need Complete Clone
**Use `web-clone-exact` skill:**
```bash
# Create 100% fidelity clone with all CSS anim + JS behavior
# Deploy live (Vercel/Netlify/Node)
```

---

## Practical Examples for Lu (elpatron)

### Scenario A: Competitor Store Analysis
**Goal:** Ambil design + layout dari competitor, buat versi lu sendiri

```bash
# 1. Extract competitor store
/home/ubuntu/tools/website-code-inspector.sh https://competitor.myshopify.com ./competitor-analyze

# 2. Review extracted files
cat ./competitor-analyze/tech-report.txt        # Framework info
ls -lh ./competitor-analyze/css/                # Get CSS sizes
head -50 ./competitor-analyze/js/inline.js      # Check JS logic

# 3. Gw bisa: Port design to KRICKEL store
# Using shopify-theme-conversion skill
```

### Scenario B: Clone Lovable Design Shopify
**Goal:** Lu punya design di Lovable, gw convert ke Shopify Liquid

```bash
# 1. Export Lovable to vercel URL
# lu: drop vercel URL

# 2. Gw extract:
/home/ubuntu/tools/website-code-inspector.sh https://your-lovable.vercel.app ./lovable-source

# 3. Gw convert:
# Load shopify-theme-conversion
# Port React components Liquid sections
# Exact 1:1 fidelity, chunked writes (300 line max)
# Push to KRICKEL test store
```

### Scenario C: Full Theme Clone Deploy
**Goal:** Ambil situs competitor, buat exact clone lu, deploy live

```bash
# 1. Extract competitor
/home/ubuntu/tools/website-code-inspector.sh https://example.com ./full-clone

# 2. Build clone with web-clone-exact skill
# All CSS anim preserved
# All JS behavior working
# Responsive on mobile

# 3. Deploy to Vercel/Netlify (lu own domain)
```

---

## Real Output Example (From Gymshark Test)

**Tech Report Generated:**
```
=== FRAMEWORK DETECTION ===
SHOPIFY THEME DETECTED
Framework: Shopify Liquid
 React/Next.js detected

=== PROGRAMMING LANGUAGES ===
JavaScript <script> tags: 4
CSS references: 2

LIQUID CODE FOUND:
{{amount}}
{{count}}
{{discount}}
... 26 more variables
```

**Files Created:**
- `source.html` (full page)
- `extracted-liquid.liquid` (29 Liquid vars)
- `css/inline.css` (0 lines)
- `css/external.css` (14 lines downloaded)
- `js/inline.js` (behavior scripts)
- `js/external.js` (framework JS)
- `tech-report.txt` (framework + language detection)
- `analysis.json` (structured data)

---

## Limitations & Gotchas

| Issue | Solution |
|-------|----------|
| JavaScript-rendered content not captured | Use browser-based tools (web-clone-exact) for SPA |
| Large files (>50MB) timeout | Reduce with curl `--max-filesize` |
| Protected/auth-required sites | Need login session or API access |
| Relative URLs broken after extract | Use `static-site-rebuild-component-based` skill |
| CORS-blocked external resources | Script downloads what's accessible; restricted resources noted |

---

## Command Cheat Sheet

```bash
# Inspect Shopify store
/home/ubuntu/tools/website-code-inspector.sh https://store.myshopify.com ./analysis

# Extract to specific folder
/home/ubuntu/tools/website-code-inspector.sh https://example.com ~/Desktop/extract

# View tech report
cat ./_website-extract/tech-report.txt

# Check what JS was extracted
wc -l ./_website-extract/js/inline.js ./_website-extract/js/external.js

# View Liquid code (if Shopify)
cat ./_website-extract/extracted-liquid.liquid

# Copy CSS to clipboard (macOS)
cat ./_website-extract/css/inline.css | pbcopy
```

---

## Integration with Hermes Skills

**After extraction, gw bisa:**

| Tool | What It Does | When to Use |
|------|-------------|------------|
| `shopify-theme-conversion` | Port extracted code Shopify Liquid | Lu ada design/competitor theme |
| `web-clone-exact` | Build 100% fidelity clone + deploy live | Lu mau exact replica with animations |
| `static-site-rebuild-component-based` | Multi-page component system | Lu ada 6+ pages, avoid duplication |
| `shopify-expert` | Reference Liquid patterns found | Understand extracted Liquid variables |

---

## Ready to Use?

**Next Steps:**

1. **Drop URL** - situs mana yang lu mau analyze?
2. **Gw run inspector** - extract + detect framework
3. **Review report** - tech stack + what was found
4. **Decide next** - clone? convert? deploy?

Bro, lu kasih aja URL target-nya. Gw gas analyze + extract + recommend workflow.
