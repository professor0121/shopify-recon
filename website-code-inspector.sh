#!/bin/bash
# Website Code Inspector & Extractor
# Detects framework, language, tech stack, dan extract code (HTML/CSS/JS/Liquid)
# Usage: ./website-code-inspector.sh https://example.com

set -e

URL="${1:-}"
OUTPUT_DIR="${2:-./_website-extract}"

if [ -z "$URL" ]; then
    echo "Usage: $0 <URL> [output_dir]"
    echo "Example: $0 https://example.myshopify.com ./output"
    exit 1
fi

echo "Inspecting: $URL"
echo "Output: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# ============================================================================
# 1. FETCH HTML + Headers
# ============================================================================
echo -e "\n[1/7] Fetching HTML + Headers..."
curl -s -L -D "$OUTPUT_DIR/headers.txt" "$URL" > "$OUTPUT_DIR/source.html"

echo "Headers saved"
grep -i "x-shopify\|content-type\|server" "$OUTPUT_DIR/headers.txt" | head -10 || true

# ============================================================================
# 2. DETECT FRAMEWORK & LANGUAGE
# ============================================================================
echo -e "\n[2/7] Detecting framework & language..."

TECH_REPORT="$OUTPUT_DIR/tech-report.txt"
> "$TECH_REPORT"

echo "=== FRAMEWORK DETECTION ===" >> "$TECH_REPORT"

# Shopify Theme Check (CRITICAL)
if grep -q "Shopify\|shopify\.com\|/cdn/shop\|Shopify.checkout\|window.Shopify" "$OUTPUT_DIR/source.html"; then
    echo "SHOPIFY THEME DETECTED" >> "$TECH_REPORT"
    echo "Framework: Shopify Liquid" >> "$TECH_REPORT"
    IS_SHOPIFY=true
else
    IS_SHOPIFY=false
fi

# React / Next.js
if grep -q "data-react-root\|__react\|__NEXT_DATA__\|_next/" "$OUTPUT_DIR/source.html"; then
    echo " React/Next.js detected" >> "$TECH_REPORT"
fi

# Vue
if grep -q "data-v-app\|#app.*vue\|__vue__" "$OUTPUT_DIR/source.html"; then
    echo "Vue.js detected" >> "$TECH_REPORT"
fi

# Lovable (Vercel Edge)
if grep -q "vercel.com\|_vercel\|data-component\|__lovable" "$OUTPUT_DIR/source.html"; then
    echo "Lovable detected (React-based)" >> "$TECH_REPORT"
fi

# TypeScript indicator
if grep -q "<script.*type=\"module\"" "$OUTPUT_DIR/source.html" || grep -q "\.tsx\|\.ts" "$OUTPUT_DIR/source.html"; then
    echo "TypeScript likely" >> "$TECH_REPORT"
fi

# Languages in scripts
echo -e "\n=== PROGRAMMING LANGUAGES ===" >> "$TECH_REPORT"
SCRIPT_COUNT=$(grep -c "<script" "$OUTPUT_DIR/source.html" || echo "0")
echo "JavaScript <script> tags: $SCRIPT_COUNT" >> "$TECH_REPORT"

# CSS
CSS_COUNT=$(grep -c "\.css\|<style" "$OUTPUT_DIR/source.html" || echo "0")
echo "CSS references: $CSS_COUNT" >> "$TECH_REPORT"

# Liquid tags (Shopify)
LIQUID_TAGS=$(grep -o "{{.*}}\|{%.*%}" "$OUTPUT_DIR/source.html" | head -5 || echo "none")
if [ "$LIQUID_TAGS" != "none" ]; then
    echo -e "\nLIQUID CODE FOUND:" >> "$TECH_REPORT"
    echo "$LIQUID_TAGS" >> "$TECH_REPORT"
fi

cat "$TECH_REPORT"

# ============================================================================
# 3. EXTRACT LIQUID CODE (If Shopify)
# ============================================================================
if [ "$IS_SHOPIFY" = true ]; then
    echo -e "\n[3/7] Extracting Liquid code..."
    
    LIQUID_FILE="$OUTPUT_DIR/extracted-liquid.liquid"
    > "$LIQUID_FILE"
    
    # Grab all {{ }} and {% %} blocks
    grep -o "{{[^}]*}}\|{%[^%]*%}" "$OUTPUT_DIR/source.html" | sort -u > "$LIQUID_FILE" 2>/dev/null || true
    
    if [ -s "$LIQUID_FILE" ]; then
        echo "Liquid code extracted ($(wc -l < "$LIQUID_FILE") lines)"
        head -20 "$LIQUID_FILE"
    fi
    
    # Try to extract theme.liquid (main template)
    THEME_LIQUID=$(sed -n '/<html/,/<\/html>/p' "$OUTPUT_DIR/source.html" | head -100)
    echo "$THEME_LIQUID" > "$OUTPUT_DIR/theme-structure.html"
fi

# ============================================================================
# 4. EXTRACT ALL STYLESHEETS (CSS)
# ============================================================================
echo -e "\n[4/7] Extracting CSS..."

CSS_DIR="$OUTPUT_DIR/css"
mkdir -p "$CSS_DIR"

# Inline <style> blocks
grep -oP '<style[^>]*>\K.*?(?=</style>)' "$OUTPUT_DIR/source.html" > "$CSS_DIR/inline.css" 2>/dev/null || true

# Extract external CSS URLs
grep -oP '<link[^>]*href="\K[^"]*\.css' "$OUTPUT_DIR/source.html" | while read url; do
    # Make URL absolute
    if [[ ! "$url" =~ ^http ]]; then
        url="$URL$url"
    fi
    echo "Downloading: $url"
    curl -s "$url" >> "$CSS_DIR/external.css" 2>/dev/null || echo "# Failed to download: $url"
done

echo "CSS extracted"
echo "  - inline: $(wc -l < "$CSS_DIR/inline.css" 2>/dev/null || echo 0) lines"
echo "  - external: $(wc -l < "$CSS_DIR/external.css" 2>/dev/null || echo 0) lines"

# ============================================================================
# 5. EXTRACT ALL JAVASCRIPT
# ============================================================================
echo -e "\n[5/7] Extracting JavaScript..."

JS_DIR="$OUTPUT_DIR/js"
mkdir -p "$JS_DIR"

# Inline <script> blocks (exclude analytics)
grep -oP '<script[^>]*>\K.*?(?=</script>)' "$OUTPUT_DIR/source.html" | \
    grep -v "gtag\|ga\.\|analytics\|hotjar\|facebook\|twitter\|ads" > "$JS_DIR/inline.js" 2>/dev/null || true

# Extract external JS URLs
grep -oP '<script[^>]*src="\K[^"]*\.js' "$OUTPUT_DIR/source.html" | while read url; do
    if [[ ! "$url" =~ ^http ]]; then
        url="$URL$url"
    fi
    echo "Downloading: $url"
    curl -s "$url" >> "$JS_DIR/external.js" 2>/dev/null || true
done

echo "JavaScript extracted"
echo "  - inline: $(wc -l < "$JS_DIR/inline.js" 2>/dev/null || echo 0) lines"
echo "  - external: $(wc -l < "$JS_DIR/external.js" 2>/dev/null || echo 0) lines"

# ============================================================================
# 6. ANALYZE STRUCTURE & DEPENDENCIES
# ============================================================================
echo -e "\n[6/7] Analyzing structure..."

cat > "$OUTPUT_DIR/analysis.json" << 'ANALYSIS'
{
  "url": "URL_PLACEHOLDER",
  "is_shopify": IS_SHOPIFY_PLACEHOLDER,
  "scripts_count": SCRIPTS_COUNT,
  "stylesheets_count": CSS_COUNT,
  "has_liquid": HAS_LIQUID_PLACEHOLDER,
  "frameworks": [
    "FRAMEWORKS_PLACEHOLDER"
  ],
  "files_extracted": {
    "html": "source.html",
    "liquid": "extracted-liquid.liquid (if Shopify)",
    "css": "css/ directory",
    "javascript": "js/ directory",
    "report": "tech-report.txt"
  }
}
ANALYSIS

# Fill placeholders
sed -i "s|URL_PLACEHOLDER|$URL|g" "$OUTPUT_DIR/analysis.json"
sed -i "s|IS_SHOPIFY_PLACEHOLDER|$IS_SHOPIFY|g" "$OUTPUT_DIR/analysis.json"
sed -i "s|SCRIPTS_COUNT|$SCRIPT_COUNT|g" "$OUTPUT_DIR/analysis.json"
sed -i "s|HAS_LIQUID_PLACEHOLDER|$([ "$IS_SHOPIFY" = true ] && echo 'true' || echo 'false')|g" "$OUTPUT_DIR/analysis.json"

echo "Structure analyzed"

# ============================================================================
# 7. SUMMARY & NEXT STEPS
# ============================================================================
echo -e "\n[7/7] Summary"
echo "=================================================="
echo "EXTRACTION COMPLETE"
echo "=================================================="
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Files generated:"
ls -lh "$OUTPUT_DIR"/ | awk '{print "  " $9 " (" $5 ")"}'
echo ""
if [ "$IS_SHOPIFY" = true ]; then
    echo "SHOPIFY THEME DETECTED"
    echo "   Liquid code: $OUTPUT_DIR/extracted-liquid.liquid"
    echo "   Theme structure: $OUTPUT_DIR/theme-structure.html"
fi
echo ""
echo "Tech Report:"
cat "$OUTPUT_DIR/tech-report.txt"
echo ""
echo "Next: Convert to standalone format if needed"
echo "   Option A: Use shopify-theme-conversion skill (for Liquid conversion)"
echo "   Option B: Use web-clone-exact skill (for complete HTML+CSS+JS clone)"
