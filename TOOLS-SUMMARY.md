# COMPLETE TOOLKIT - Extract Code Dalaman dari Website
**Semua Tools Installed & Ready | Kiro | 2026-06-21**

---

## TOOLS INSTALLED (3 Deobfuscators Ready)

| Tool | Purpose | Status | Command |
|------|---------|--------|---------|
| **webcrack** | Unbundle + deobfuscate JS | Ready | `webcrack file.js --output clean.js` |
| **javascript-deobfuscator** | General deobfuscation | Ready | `javascript-deobfuscator < file.js > clean.js` |
| **js-deobfuscator** | AST-based deobfuscation | Ready | `js-deobfuscator file.js > clean.js` |

---

## 3 EXTRACTION WORKFLOWS AVAILABLE

### Workflow 1: Website Code Inspector (Framework Detection)
**Extract HTML, CSS, JS + detect tech stack**

```bash
/home/ubuntu/tools/website-code-inspector.sh <URL> [output_dir]
```

**Output:**
- `source.html` - Full HTML source
- `css/` - Stylesheets
- `js/` - JavaScript (raw + deobfuscated)
- `tech-report.txt` - Framework detection (Shopify/React/Vue/etc)
- `analysis.json` - Structured data

**Example:**
```bash
/home/ubuntu/tools/website-code-inspector.sh https://example.com ./extract
cat ./extract/tech-report.txt
```

---

### Workflow 2: Deep Code Extractor (Deobfuscation + Analysis)
**Download all JS, deobfuscate, extract logic + API calls**

```bash
/home/ubuntu/tools/deep-code-extractor.sh <URL> [output_dir]
```

**Output:**
- `raw/` - Original JS files
- `deobfuscated/` - Readable JS (webcrack + deobfuscators)
- `extracted-logic/` - API endpoints, functions, potential secrets
- `analysis/REPORT.md` - Full analysis report
- `SUMMARY.txt` - Quick reference

**Example:**
```bash
/home/ubuntu/tools/deep-code-extractor.sh https://example.com ./analysis
cat ./analysis/SUMMARY.txt
ls -lh ./analysis/deobfuscated/
grep "function\|const.*=" ./analysis/deobfuscated/*.js | head -20
```

---

### Workflow 3: Manual Deobfuscation (For Specific Files)
**Deobfuscate individual JS files**

```bash
# Try webcrack first (most comprehensive)
webcrack minified.js --output readable.js

# Or use javascript-deobfuscator
javascript-deobfuscator < minified.js > readable.js

# Or AST-based
js-deobfuscator minified.js > readable.js
```

---

## REAL EXAMPLE: What You Get

### Input: Obfuscated JavaScript
```javascript
var _0x5a46=['length','split'];
(function(_0x4e2a30){
  var _0x57e29=function(_0x2fb26c){
    while(--_0x2fb26c){_0x4e2a30['push'](_0x4e2a30['shift']());}
  };_0x57e29(++_0x4e2a30);
})(_0x5a46);
```

### Output: After webcrack
```javascript
var _0x5a46 = ["length", "split"];
(function (_0x4e2a30) {
  function _0x57e29(_0x2fb26c) {
    while (--_0x2fb26c) {
      _0x4e2a30.push(_0x4e2a30.shift());
    }
  }
  _0x57e29(++_0x4e2a30);
})(_0x5a46);
```

**Result:** Variable names still obfuscated, but structure + logic now readable. Dapat extract function patterns, API calls, flow logic.

---

## COMMON USE CASES

### Use Case 1: Understand Competitor's Feature Logic
```bash
# Extract competitor site
/home/ubuntu/tools/deep-code-extractor.sh https://competitor.com ./comp-analysis

# Search for specific feature
grep -n "filter\|search\|checkout" ./comp-analysis/deobfuscated/*.js

# View function
sed -n '100,150p' ./comp-analysis/deobfuscated/main.js
```

### Use Case 2: Find API Endpoints
```bash
# Extract + analyze
/home/ubuntu/tools/deep-code-extractor.sh https://example.com ./analysis

# View all endpoints
cat ./analysis/extracted-logic/api-endpoints.txt

# Search for specific endpoint
grep "/products\|/api/cart\|/checkout" ./analysis/deobfuscated/*.js
```

### Use Case 3: Extract Secret Keys / Config
```bash
# Extract + analyze
/home/ubuntu/tools/deep-code-extractor.sh https://example.com ./analysis

# Check potential secrets
cat ./analysis/extracted-logic/potential-keys.txt

# Note: Usually public keys or test credentials, not actual secrets
```

### Use Case 4: Learn from Reference Code
```bash
# Extract Shopify/official themes from GitHub
git clone https://github.com/Shopify/dawn
cd dawn/sections

# Study Liquid + JS patterns
cat featured-products.liquid
```

---

## IMPORTANT LIMITATIONS

| Limitation | Reason | Workaround |
|-----------|--------|-----------|
| CloudFront blocks external bundles | Security headers (CORS, access deny) | Use inline scripts + deobfuscate those |
| Source maps not always available | Teams remove them in production | Use deobfuscator to reverse logic |
| Webpack bundles are large | Tree-shaking + minification | Focus on specific feature = search grep |
| API keys in code are usually public | Developers use test/sandbox keys | Don't assume they're actual credentials |
| JavaScript-rendered content missing | Inspector captures HTML, not rendered DOM | Use Puppeteer/Playwright for SPA |

---

## QUICK START COMMANDS

```bash
# 1. Extract website code (framework detection)
/home/ubuntu/tools/website-code-inspector.sh https://example.com ./extract

# 2. Deep analysis (deobfuscate + extract logic)
/home/ubuntu/tools/deep-code-extractor.sh https://example.com ./analysis

# 3. View results
cat ./analysis/SUMMARY.txt
cat ./analysis/analysis/REPORT.md
ls -lh ./analysis/deobfuscated/

# 4. Search for specific logic
grep -r "function\|const.*=>.*{" ./analysis/deobfuscated/ | head -20
grep -r "fetch\|axios\|api" ./analysis/deobfuscated/ | head -10

# 5. Deobfuscate single file manually
webcrack ./analysis/raw/main.js --output ./main-readable.js
cat ./main-readable.js
```

---

## REFERENCE: Tools Available

### Official Shopify Tools
- `shopify` CLI - Theme management (v4.2.0 installed)
- `shopify-theme-inspector` - Chrome DevTools for Liquid profiling

### Code Extraction Tools (Installed)
- `webcrack` - Unbundle + deobfuscate (2742)
- `javascript-deobfuscator` - General deobfuscator (1129)
- `js-deobfuscator` - AST-based deobfuscator (1142)

### Custom Scripts (Created)
- `/home/ubuntu/tools/website-code-inspector.sh` - Framework detection + code download
- `/home/ubuntu/tools/deep-code-extractor.sh` - Full pipeline: download + deobfuscate + analyze

### Reference Themes (Clone from GitHub)
- `Shopify/dawn` (3021) - Official reference
- `Shopify/skeleton-theme` (737) - Minimal scaffold
- `Shopify/Timber` (1171) - Advanced framework

---

## WORKFLOW FOR LU (elpatron)

**Goal: Extract logic from website Adapt to SYNC theme**

### Step 1: Extract & Analyze
```bash
/home/ubuntu/tools/deep-code-extractor.sh https://target-store.myshopify.com ./target-analysis
```

### Step 2: Review Report
```bash
cat ./target-analysis/SUMMARY.txt
cat ./target-analysis/analysis/REPORT.md
```

### Step 3: Find Specific Feature
```bash
# Example: Find product filtering logic
grep -n "filter\|search" ./target-analysis/deobfuscated/*.js | head -20
```

### Step 4: Extract & Adapt
```bash
# Copy relevant function
sed -n '50,100p' ./target-analysis/deobfuscated/main.js > /tmp/filter-logic.js

# Review in VS Code
code /tmp/filter-logic.js

# Adapt to SYNC theme (use Lovable or Liquid)
```

### Step 5: Test on KRICKEL
```bash
# Push to test store
shopify theme push --store krickel.myshopify.com --theme 161562329345
```

---

## DELIVERABLES YOU NOW HAVE

| Item | Location | Use |
|------|----------|-----|
| Website inspector | `/home/ubuntu/tools/website-code-inspector.sh` | Detect framework + extract code |
| Deep extractor | `/home/ubuntu/tools/deep-code-extractor.sh` | Full deobfuscation pipeline |
| Deobfuscators (3x) | NPM global (`webcrack`, etc) | Manual deobfuscation |
| Shopify CLI | `/home/ubuntu/.local/bin/shopify` | Theme management |
| Documentation | `/home/ubuntu/tools/*.md` | Reference guides |

---

## NEXT STEPS

**Choose one:**

1. **Extract Competitor Store**
   - Drop competitor URL
   - Gw extract + analyze
   - Gw identify features
   - Gw recommend adaptation for SYNC

2. **Analyze Your Own SYNC Theme**
   - Pull SYNC from KRICKEL test store
   - Beautify + optimize JS
   - Document logic

3. **Learn from Official Themes**
   - Clone Shopify/dawn
   - Study Liquid + JS patterns
   - Port to SYNC

4. **Custom Feature Extraction**
   - Tell gw what feature (checkout, filtering, etc)
   - Gw extract + explain logic
   - Gw adapt to SYNC

---

**Bro, lu siap? Drop target URL atau feature yang mau lu analyze.**
