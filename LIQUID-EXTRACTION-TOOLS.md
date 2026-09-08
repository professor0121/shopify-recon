# SHOPIFY LIQUID CODE EXTRACTION TOOLS
**Kompilasi Tools GitHub + Community | Kiro | 2026-06-21**

## TOP TOOLS UNTUK EXTRACT & VIEW LIQUID CODE

### 1. OFFICIAL SHOPIFY TOOLS

#### A. Shopify CLI (Official)
**RECOMMENDED**
- **Repo:** `Shopify/cli` (714)
- **Function:** Download + push + watch theme files
- **Install:** `npm install -g @shopify/cli`
- **Command:**
```bash
shopify theme pull --store mystore.myshopify.com --theme 123456
# Downloads ALL Liquid files locally
```
- **Status:** Already installed on your system
- **Best for:** Official, production-grade, full theme sync

#### B. Theme Kit (Legacy but still works)
****
- **Repo:** `Shopify/themekit` (1303)
- **Function:** CLI tool to manage theme assets
- **Install:** `brew install themekit` (macOS) or `choco install themekit` (Windows)
- **Command:**
```bash
theme get --password=xxx --store=mystore.myshopify.com --themeid=123456
# Downloads theme to local folder
```
- **Status:** Legacy but works; Shopify recommends CLI instead

#### C. Shopify Theme Inspector (Chrome DevTools)
****
- **Repo:** `Shopify/shopify-theme-inspector` (179)
- **Function:** Chrome extension to profile Liquid render times
- **Install:** Chrome Web Store
- **Best for:** Debug Liquid performance, find slow sections

---

### 2. COMMUNITY TOOLS FOR LIQUID EXTRACTION

#### A. download-shopify-theme (Direct Liquid Extract)
****
- **Repo:** `lizrice/download-shopify-theme` (4but FOCUSED)
- **Function:** CLI to download Liquid files from public theme
- **Install:**
```bash
git clone https://github.com/lizrice/download-shopify-theme
cd download-shopify-theme
npm install
```
- **Command:**
```bash
node index.js --store mystore.myshopify.com --theme-id 123456
# Extracts Liquid files only
```
- **Best for:** Quick extraction when Theme Access token not available

#### B. Shopify Theme Lab (Development Environment)
****
- **Repo:** `uicrooks/shopify-theme-lab` (816)
- **Function:** Dev environment with Liquid + Vue + Tailwind
- **Install:**
```bash
npm install -g @uicrooks/shopify-theme-lab
theme-lab create my-theme
```
- **Best for:** Build + test new themes locally

#### C. vscode-liquid (VS Code Extension)
****
- **Repo:** `panoply/vscode-liquid` (182)
- **Function:** Liquid syntax highlighting + autocomplete in VS Code
- **Install:** VS Code Extensions Search "Liquid"
- **Best for:** Edit extracted Liquid files with proper syntax support

#### D. Shopify Packer (Webpack-based Build)
****
- **Repo:** `hayes0724/shopify-packer` (179)
- **Function:** Modern build tool for Shopify theme development
- **Install:**
```bash
npm install -g @hayes0724/shopify-packer
packer create my-theme
```
- **Best for:** Build pipeline + asset optimization

---

### 3. THEME FRAMEWORKS (Source Code Available)

#### A. Dawn (Official Reference Theme)
**BEST REFERENCE**
- **Repo:** `Shopify/dawn` (3021)
- **What it is:** Official Shopify reference theme, Open Store 2.0 ready
- **Get it:**
```bash
git clone https://github.com/Shopify/dawn
cd dawn
# Full Liquid source code available
```
- **Best for:** Learn Liquid best practices from Shopify engineers

#### B. Skeleton Theme (Minimal Scaffold)
****
- **Repo:** `Shopify/skeleton-theme` (737)
- **What it is:** Minimal theme scaffold with Shopify best practices
- **Get it:**
```bash
git clone https://github.com/Shopify/skeleton-theme
```
- **Best for:** Start from clean, minimal codebase

#### C. Timber (Advanced Framework)
****
- **Repo:** `Shopify/Timber` (1171)
- **What it is:** Ultimate Shopify theme framework
- **Get it:**
```bash
git clone https://github.com/Shopify/Timber
```
- **Best for:** Advanced theme architecture patterns

---

### 4. UTILITY TOOLS

#### A. Shopify Theme (Console Tool for Assets)
****
- **Repo:** `Shopify/shopify_theme` (654)
- **Function:** Ruby gem to interact with theme assets
- **Install:**
```bash
gem install shopify_theme
```
- **Command:**
```bash
shopify_theme download -s mystore -t 123456 -a "admin-token"
```
- **Best for:** Asset management, Ruby environment

#### B. Slate (Legacy Toolkit)
****
- **Repo:** `Shopify/slate` (1285)
- **Status:** Deprecated (use Shopify CLI instead)
- **Why mentioned:** Many projects still use it; good learning resource

---

## PRACTICAL WORKFLOW FOR YOU (elpatron)

### Scenario 1: Extract Competitor Theme Liquid Code
**Goal:** View + steal design from competitor Shopify store

**Step 1: Use Shopify CLI (Official)**
```bash
# If theme is public (admin access needed):
shopify theme pull --store competitor.myshopify.com --theme 123456

# Output: All Liquid files in ./theme/ folder
```

**Step 2: View Liquid Code**
```bash
# Browse extracted files
cat ./theme/sections/header.liquid
cat ./theme/templates/product.liquid
cat ./theme/snippets/product-card.liquid
```

**Step 3: Analyze with VS Code**
```bash
# Install vscode-liquid extension
code ./theme/
# Syntax highlighting + autocomplete
```

**Step 4: Port to Your Store**
```bash
# Modify Liquid to match your brand
# Use shopify-theme-conversion skill to adapt

# Push to KRICKEL test store
shopify theme push --store krickel.myshopify.com --theme 161562329345
```

---

### Scenario 2: Clone Public Theme (No Admin Access)

**Step 1: Use download-shopify-theme**
```bash
# Download theme without Theme Access token
node download-shopify-theme/index.js \
  --store mystore.myshopify.com \
  --theme-id 123456

# Output: Liquid files extracted
```

**Step 2: Analyze Structure**
```bash
# See what files were extracted
find ./extracted-theme -type f -name "*.liquid" | head -20

# Count sections/templates
find ./extracted-theme/sections -name "*.liquid" | wc -l
find ./extracted-theme/templates -name "*.liquid" | wc -l
```

---

### Scenario 3: Study Official Themes (No Extraction Needed)

**Step 1: Clone from GitHub**
```bash
# Use GitHub repos (no API call needed)
git clone https://github.com/Shopify/dawn
cd dawn

# Browse Liquid code
cat ./sections/hero-banner.liquid
cat ./sections/featured-products.liquid
```

**Step 2: Learn Best Practices**
```bash
# Study how Shopify structures themes
tree ./sections/      # See all sections
tree ./templates/     # See all templates
tree ./snippets/      # See all snippets
```

**Step 3: Copy Patterns to SYNC Theme**
```bash
# Take patterns you like
# Adapt to SYNC theme
# Push to KRICKEL

# Example: Copy featured-products section
cp dawn/sections/featured-products.liquid \
   sync-license-src/sections/featured-products-custom.liquid
```

---

## TOOL COMPARISON TABLE

| Tool | Best For | Access | Ease | Stars |
|------|----------|--------|------|-------|
| **Shopify CLI** | Official extract | Admin token | Easy | 714 |
| **Theme Kit** | Legacy support | Admin token | Medium | 1303 |
| **download-shopify-theme** | Public themes | None needed | Medium | 4 |
| **vscode-liquid** | Code editing | Local files | Easy | 182 |
| **Shopify Theme Inspector** | Debug perf | Chrome ext | Easy | 179 |
| **Shopify Theme Lab** | Dev env | None | Hard | 816 |
| **Dawn (GitHub)** | Learn patterns | Clone | Easy | 3021 |
| **Skeleton Theme** | Start scaffold | Clone | Easy | 737 |

---

## WHAT GATHERS LIQUID CODE

### Method 1: Extract from Live Store (Admin Required)
```bash
# Official way - need Theme Access token or admin login
shopify theme pull --store mystore.myshopify.com
# Gets ACTUAL theme from store

# Best for: Your own store, authorized stores
```

### Method 2: Download from Public Theme (No Auth)
```bash
# Community tools - works on public stores
node download-shopify-theme/index.js --store store.myshopify.com
# Gets theme files visible to public

# Best for: Competitor analysis, learning
```

### Method 3: Clone from GitHub (Reference Themes)
```bash
# Use open-source theme repos
git clone https://github.com/Shopify/dawn
# Gets official reference code

# Best for: Study best practices, learn patterns
```

### Method 4: Inspect via Browser (Limited)
```bash
# Website code inspector (gw buat tadi)
/home/ubuntu/tools/website-code-inspector.sh \
  https://store.myshopify.com \
  ./extract
# Extracts HTML-rendered Liquid
# Finds Liquid variables in templates

# Best for: Quick analysis, no admin access
```

---

## NEXT STEPS FOR LU

**Choose one:**

### Option A: Extract from Specific Shopify Store
- Kasih tau store URL
- Gw check kalau ada Theme Access token
- Gw pull dengan Shopify CLI
- Gw analyze Liquid code
- Gw report back findings

### Option B: Study Official Themes
- Recommend: Clone `Shopify/dawn` atau `Shopify/skeleton-theme`
- Gw analyze + explain Liquid patterns
- Gw port patterns to SYNC theme

### Option C: Analyze Competitor Design
- Drop competitor URL
- Gw extract dengan website inspector
- Gw identify tech stack + Liquid usage
- Gw recommend how to port

### Option D: Setup Local Development
- Install Shopify CLI (udah ada)
- Install vscode-liquid extension
- Pull theme locally
- Edit Liquid with proper syntax support
- Push back to store

**Bro, pilih mana? Kasih tau store URL atau design reference-nya.**
