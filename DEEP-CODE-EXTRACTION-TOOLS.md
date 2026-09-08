# DEEP CODE EXTRACTION TOOLS - Bongkar Dalaman Web
**Extract JS Logic, Deobfuscate, Unbundle, Extract Source Maps | Kiro | 2026-06-21**

## TOP TOOLS - Installable & Siap Pakai

### TIER 1: Deobfuscate + Unpack JavaScript (PALING POWERFUL)

#### 1. webcrack (RECOMMENDED)
**BEST**
- **Repo:** `j4k0xb/webcrack` (2742)
- **Function:** Deobfuscate obfuscator.io, unminify, unpack bundled JS
- **What it does:**
  - Reverse obfuscation (Obfuscator.io, javascript-obfuscator)
  - Unpack webpack bundles
  - Unminify JS
  - Beautify code
  - Extract readable logic

**Install:**
```bash
npm install -g webcrack
# atau
git clone https://github.com/j4k0xb/webcrack
cd webcrack
npm install
npm run build
```

**Usage:**
```bash
# Local file
webcrack input.js --output output.js

# From URL
webcrack --url https://example.com/bundle.js --output output.js

# Unpack webpack
webcrack --webpack bundle.js

# Output: Readable JS file with logic intact
```

**Best for:** Main tool untuk extract logic dari bundled/obfuscated code

---

#### 2. js-deobfuscator (CLI + Web)
****
- **Repo:** `kuizuo/js-deobfuscator` (1142)
- **Function:** Automated deobfuscation berbasis Babel AST
- **Features:**
  - Online playground
  - CLI tool
  - Programmable API
  - AST-based approach (reliable)

**Install:**
```bash
npm install -g js-deobfuscator
# atau
npm install @kuizuo/js-deobfuscator
```

**Usage:**
```bash
# CLI
js-deobfuscator input.js > output.js

# Programmatically
const { deobfuscate } = require('@kuizuo/js-deobfuscator');
const result = deobfuscate(obfuscatedCode);
console.log(result.code);
```

**Web:** https://deobfuscator.kuizuo.cn/ (online tool)

---

#### 3. de4js (Web + Unpacker)
****
- **Repo:** `lelinhtinh/de4js` (1580)
- **Function:** Deobfuscator and unpacker
- **Features:**
  - Remove dead code
  - Fix eval() calls
  - Unpack various formats

**Install:**
```bash
git clone https://github.com/lelinhtinh/de4js
cd de4js
npm install
npm run build
```

**Web:** https://lelinhtinh.github.io/de4js/

---

#### 4. javascript-deobfuscator (General Purpose)
****
- **Repo:** `ben-sb/javascript-deobfuscator` (1129)
- **Function:** General purpose deobfuscator
- **Features:**
  - Handle various obfuscation types
  - Reliable for common cases

**Install:**
```bash
npm install -g javascript-deobfuscator
```

**Usage:**
```bash
javascript-deobfuscator < obfuscated.js > readable.js
```

---

### TIER 2: Source Maps + Asset Extraction

#### 5. unmapx (Source Map Extractor)
****
- **Repo:** `incogbyte/unmapx` (7but FOCUSED)
- **Function:** Extract + unpack JavaScript source maps
- **Why important:** Source maps = original code before minify/bundle
- **Features:**
  - Extract from .map files
  - Extract from inline base64
  - URL extraction
  - Indexed source maps support

**Install:**
```bash
git clone https://github.com/incogbyte/unmapx
cd unmapx
npm install
```

**Usage:**
```bash
# From .map file
node unmapx.js --file bundle.js.map

# From URL
node unmapx.js --url https://example.com/bundle.js.map

# Inline base64
node unmapx.js --inline "sourceMappingURL=data:..."

# Output: Original source files
```

**Best for:** Extract original source jika .map file available

---

#### 6. SingleFile (Complete Website Capture)
**BROWSER EXTENSION**
- **Repo:** `gildas-lormeau/SingleFile`
- **Function:** Capture website sebagai single HTML file (semua resource inline)
- **Why useful:** Extract ALL assets (JS, CSS, images) dalam 1 file

**Install:**
```bash
# Chrome Web Store
# https://chrome.google.com/webstore/detail/singlefile/mpiodijhokgodhhofbcjdecpffjipkle

# Firefox Add-on
# https://addons.mozilla.org/en-US/firefox/addon/single-file/
```

**CLI version:**
```bash
npm install -g single-file-cli
single-file https://example.com --output-file output.html
# Semua JS/CSS/images embedded dalam 1 file
```

---

### TIER 3: Code Analysis + Inspection

#### 7. Chrome DevTools Protocol Playbook
**(Reference)**
- **Repo:** `roderickch01/chrome-cdp-playbook`
- **Function:** Reverse-engineer SPAs + Electron apps
- **Method:** CDP (Chrome DevTools Protocol)
- **Why useful:** Inspect network calls, intercepted requests, runtime state

**Setup:**
```bash
# Use Chrome DevTools or Puppeteer + CDP
npm install puppeteer

# Script untuk inspect network
const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.on('response', response => {
  console.log(response.url(), response.status());
});
await page.goto('https://example.com');
```

---

## COMPARISON TABLE: Tools by Use Case

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| Unbundle + deobfuscate JS | **webcrack** | Most comprehensive, 2700|
| Extract source maps | **unmapx** | Designed for .map extraction |
| AST-based deobfuscation | **js-deobfuscator** | Reliable, Babel-based |
| General deobfuscate | **javascript-deobfuscator** | Solid alternative |
| Capture entire website | **SingleFile** | All assets in 1 file |
| Network inspection | **Chrome DevTools** | Built-in, powerful |
| Fix obfuscator.io | **js-deobfuscator** or **webcrack** | Both handle it |

---

## WORKFLOW FOR DEEP CODE EXTRACTION (elpatron)

### Step 1: Capture Website
```bash
# Use website inspector gw tadi
/home/ubuntu/tools/website-code-inspector.sh https://example.com ./extract

# Output: HTML + all linked CSS/JS
```

### Step 2: Extract All JavaScript Files
```bash
# Copy all downloaded JS to working dir
mkdir ~/code-analysis
cd ~/code-analysis
cp ~/extract/js/* .

# List what you got
ls -lh *.js
```

### Step 3: Deobfuscate + Unpack
```bash
# Install webcrack (main tool)
npm install -g webcrack

# Deobfuscate each file
for file in *.js; do
  echo "Processing $file..."
  webcrack "$file" --output "${file%.js}-clean.js"
done

# Result: Readable JS files with logic exposed
ls -lh *-clean.js
```

### Step 4: Extract Source Maps (if available)
```bash
# Install unmapx
npm install -g unmapx

# Download .map files
curl -o bundle.js.map https://example.com/bundle.js.map

# Extract original sources
node unmapx.js --file bundle.js.map

# Result: Original source code before minification
```

### Step 5: Analyze Logic
```bash
# Open readable JS in VS Code
code *-clean.js

# Search for specific functions
grep -n "function\|const.*=.*=>.*{" *-clean.js | head -20

# Find API calls
grep -n "fetch\|XMLHttpRequest\|axios" *-clean.js
```

### Step 6: Extract Key Logic
```bash
# Example: Find how they handle checkout
grep -A 10 "checkout\|payment\|cart" bundle-clean.js

# Find API endpoints
grep -o "https://[^\"']*" bundle-clean.js | sort -u

# Find variable assignments
grep -n "const.*=.*{" bundle-clean.js | head -20
```

---

## PRACTICAL EXAMPLE: Extract Competitor JS Logic

### Goal: Understand how competitor site does product filtering

**Step 1: Download competitor JS**
```bash
/home/ubuntu/tools/website-code-inspector.sh \
  https://competitor.myshopify.com \
  ./competitor-analysis
```

**Step 2: Beautify + deobfuscate**
```bash
cd competitor-analysis/js
webcrack inline.js --output inline-readable.js
webcrack external.js --output external-readable.js
```

**Step 3: Find filtering logic**
```bash
# Search for filter function
grep -n "filter\|search\|product" inline-readable.js | head -20

# Find what happens on filter click
grep -B 5 -A 10 "onClick.*filter\|addEventListener.*filter" inline-readable.js
```

**Step 4: Extract reusable code**
```bash
# Copy relevant function to your codebase
sed -n '100,150p' inline-readable.js > ~/projects/sync-license-src/filter-logic.js

# Adapt to SYNC theme
# Use Lovable to rebuild with your brand
```

---

## TOOLS INSTALL QUICK START

### Install All Main Tools
```bash
# Deobfuscator tools
npm install -g webcrack
npm install -g js-deobfuscator
npm install -g javascript-deobfuscator

# Source map extractor
npm install -g incogbyte/unmapx

# SingleFile CLI
npm install -g single-file-cli

# Optional: Puppeteer for headless inspection
npm install -g puppeteer
```

### Verify Installation
```bash
webcrack --version
js-deobfuscator --help
single-file-cli --help
```

---

## IMPORTANT LEGAL NOTE

**LEGAL USES:**
- Extract from **your own websites**
- Extract from **open-source projects**
- Extract for **security research** (with permission)
- Extract from **reference/educational material**

**NOT LEGAL:**
- Extract from competitors to **reverse-engineer proprietary logic** (IP theft)
- Extract to **bypass security protections** (circumvention)
- Extract **without authorization** from protected sites

**Best practice:** Use extracted code for **learning patterns** and **design inspiration**, not direct copying.

---

## NEXT STEPS FOR LU

**Pick a use case:**

### Option A: Extract Competitor Design Logic
- Drop competitor URL
- Gw extract dengan website inspector
- Gw deobfuscate JS
- Gw identify key patterns
- Gw adapt untuk SYNC theme

### Option B: Analyze Your Own Theme
- Pull SYNC theme locally
- Beautify JS (remove obfuscation if any)
- Document logic
- Optimize performance

### Option C: Learn from Reference Themes
- Clone Shopify/dawn dari GitHub
- Analyze clean, production-grade JS
- Reuse patterns

**Bro, mau gw install semua tools? Atau mau test pada specific URL dulu?**
