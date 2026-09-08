#!/bin/bash
# DEEP CODE EXTRACTOR - Extract + Deobfuscate + Beautify JavaScript
# Kiro | 2026-06-21
# Usage: ./deep-code-extractor.sh <URL> [output_dir]

set -e

URL="${1:-}"
OUTPUT_DIR="${2:-./_code-analysis}"

if [ -z "$URL" ]; then
  echo "Usage: ./deep-code-extractor.sh <URL> [output_dir]"
  echo "Example: ./deep-code-extractor.sh https://example.com ./analysis"
  exit 1
fi

echo "Deep Code Extraction Starting..."
echo "Target: $URL"
echo "Output: $OUTPUT_DIR"
echo ""

# Create directory structure
mkdir -p "$OUTPUT_DIR"/{raw,deobfuscated,source-maps,analysis,extracted-logic}

# ============================================================================
# STEP 1: Download all JavaScript files
# ============================================================================
echo "[1/8] Downloading JavaScript files..."

TEMP_HTML=$(mktemp)
curl -s -A "Mozilla/5.0" "$URL" > "$TEMP_HTML" 2>/dev/null || {
  echo "Failed to fetch $URL"
  exit 1
}

# Extract script URLs
grep -o 'src="[^"]*\.js"' "$TEMP_HTML" | sed 's/src="//;s/"$//' > "$OUTPUT_DIR/script-urls.txt" 2>/dev/null || true

# Also check for inline scripts
grep -o '<script[^>]*>' "$TEMP_HTML" | grep -o 'src="[^"]*"' | sed 's/src="//;s/"$//' >> "$OUTPUT_DIR/script-urls.txt" 2>/dev/null || true

# Download all JS files
SCRIPT_COUNT=0
while IFS= read -r JS_URL; do
  if [ -z "$JS_URL" ]; then continue; fi
  
  # Convert relative URLs to absolute
  if [[ ! "$JS_URL" =~ ^https?:// ]]; then
    JS_URL="${URL%/}/$JS_URL"
  fi
  
  FILENAME=$(basename "$JS_URL" | cut -d'?' -f1)
  if [ -z "$FILENAME" ] || [ "$FILENAME" = "js" ]; then
    FILENAME="script-$SCRIPT_COUNT.js"
  fi
    
  # Clean up filename
  FILENAME=$(echo "$FILENAME" | tr -d '\\')
  if [ ${#FILENAME} -eq 0 ]; then
    FILENAME="script-$SCRIPT_COUNT.js"
  fi
  
  echo "   Downloading: $JS_URL"
  curl -s -A "Mozilla/5.0" -e "$URL" -H "Referer: $URL" "$JS_URL" > "$OUTPUT_DIR/raw/$FILENAME" 2>/dev/null && echo "    Saved as $FILENAME" || echo "    Failed"
  
  SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
done < "$OUTPUT_DIR/script-urls.txt"

# Extract inline scripts
INLINE_COUNT=$(grep -c '<script>' "$TEMP_HTML" || true)
if [ "$INLINE_COUNT" -gt 0 ]; then
  echo "  Found $INLINE_COUNT inline scripts"
  # Save inline scripts
  sed -n '/<script>/,/<\/script>/p' "$TEMP_HTML" | sed 's/<\/?script>//g' > "$OUTPUT_DIR/raw/inline-scripts.js" 2>/dev/null || true
fi

echo "Downloaded $SCRIPT_COUNT external + $INLINE_COUNT inline scripts"
echo ""

# ============================================================================
# STEP 2: Deobfuscate all JavaScript files
# ============================================================================
echo "[2/8] Deobfuscating JavaScript..."

JS_FILES=$(find "$OUTPUT_DIR/raw" -name "*.js" -type f 2>/dev/null | wc -l)
PROCESSED=0

for js_file in "$OUTPUT_DIR/raw"/*.js; do
  if [ ! -f "$js_file" ]; then continue; fi
  
  FILENAME=$(basename "$js_file")
  echo "  Processing: $FILENAME"
  
  # Try webcrack first (most comprehensive)
  if webcrack "$js_file" --output "$OUTPUT_DIR/deobfuscated/$FILENAME" 2>/dev/null; then
    echo "    Deobfuscated with webcrack"
  else
    # Fallback to javascript-deobfuscator
    if javascript-deobfuscator < "$js_file" > "$OUTPUT_DIR/deobfuscated/$FILENAME" 2>/dev/null; then
      echo "    Deobfuscated with javascript-deobfuscator"
    else
      # Copy original if deobfuscation fails
      cp "$js_file" "$OUTPUT_DIR/deobfuscated/$FILENAME"
      echo "     Copied original (no deobfuscation needed?)"
    fi
  fi
  
  PROCESSED=$((PROCESSED + 1))
done

echo "Deobfuscated $PROCESSED files"
echo ""

# ============================================================================
# STEP 3: Extract source maps
# ============================================================================
echo "[3/8] Checking for source maps..."

# Look for .map file references in HTML
MAP_COUNT=$(grep -o '\.map' "$TEMP_HTML" | wc -l || true)

if [ "$MAP_COUNT" -gt 0 ]; then
  echo "  Found $MAP_COUNT source map references"
  
  grep -o 'href="[^"]*\.map"' "$TEMP_HTML" | sed 's/href="//;s/"$//' > "$OUTPUT_DIR/map-urls.txt" 2>/dev/null || true
  grep -o 'src="[^"]*\.map"' "$TEMP_HTML" | sed 's/src="//;s/"$//' >> "$OUTPUT_DIR/map-urls.txt" 2>/dev/null || true
  
  while IFS= read -r MAP_URL; do
    if [ -z "$MAP_URL" ]; then continue; fi
    
    if [[ ! "$MAP_URL" =~ ^https?:// ]]; then
      MAP_URL="${URL%/}/$MAP_URL"
    fi
    
    FILENAME=$(basename "$MAP_URL")
    echo "   Downloading map: $FILENAME"
    curl -s -A "Mozilla/5.0" "$MAP_URL" > "$OUTPUT_DIR/source-maps/$FILENAME" 2>/dev/null && echo "    Saved" || echo "    Failed"
  done < "$OUTPUT_DIR/map-urls.txt"
  
  echo "Source maps extracted"
else
  echo "  ℹ No source maps found"
fi
echo ""

# ============================================================================
# STEP 4: Extract API calls + endpoints
# ============================================================================
echo "[4/8] Extracting API calls & endpoints..."

# Search for API patterns
grep -roh 'https://[^"'\'']*/api[^"'\'']* ' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u > "$OUTPUT_DIR/extracted-logic/api-endpoints.txt" || true
grep -roh 'fetch(["\x27][^"'\'']*/[^"'\'']* ' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u >> "$OUTPUT_DIR/extracted-logic/api-endpoints.txt" || true
grep -roh 'axios\.[a-z]*(["\x27][^"'\'']*/[^"'\'']* ' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u >> "$OUTPUT_DIR/extracted-logic/api-endpoints.txt" || true

ENDPOINT_COUNT=$(wc -l < "$OUTPUT_DIR/extracted-logic/api-endpoints.txt" 2>/dev/null || echo "0")
echo "Found $ENDPOINT_COUNT API endpoints"

# Extract secret keys/tokens
echo ""
echo "[5/8] Searching for secrets (API keys, tokens)..."
grep -roh '["\x27]sk_[a-zA-Z0-9]*["\x27]' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u > "$OUTPUT_DIR/extracted-logic/potential-keys.txt" || true
grep -roh '["\x27]pk_[a-zA-Z0-9]*["\x27]' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u >> "$OUTPUT_DIR/extracted-logic/potential-keys.txt" || true
grep -roh '["\x27]Bearer [a-zA-Z0-9_.-]*["\x27]' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sort -u >> "$OUTPUT_DIR/extracted-logic/potential-keys.txt" || true

KEY_COUNT=$(wc -l < "$OUTPUT_DIR/extracted-logic/potential-keys.txt" 2>/dev/null || echo "0")
echo " Found $KEY_COUNT potential sensitive values"
if [ "$KEY_COUNT" -gt 0 ]; then
  echo "  Tip: Check 'potential-keys.txt' - may include public keys or test credentials"
fi
echo ""

# ============================================================================
# STEP 6: Extract function definitions
# ============================================================================
echo "[6/8] Extracting function definitions..."

grep -roh 'function [a-zA-Z_$][a-zA-Z0-9_$]*(' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sed 's/function //;s/($//' | sort -u > "$OUTPUT_DIR/extracted-logic/functions.txt" || true
grep -roh 'const [a-zA-Z_$][a-zA-Z0-9_$]* = (' "$OUTPUT_DIR/deobfuscated/" 2>/dev/null | sed 's/const //;s/ = ($//' | sort -u >> "$OUTPUT_DIR/extracted-logic/functions.txt" || true

FUNC_COUNT=$(wc -l < "$OUTPUT_DIR/extracted-logic/functions.txt" 2>/dev/null || echo "0")
echo "Found $FUNC_COUNT unique functions"
echo ""

# ============================================================================
# STEP 7: Generate analysis report
# ============================================================================
echo "[7/8] Generating analysis report..."

cat > "$OUTPUT_DIR/analysis/REPORT.md" << EOF
# Deep Code Analysis Report
**Generated:** $(date)
**Target:** $URL

## Summary

| Metric | Count |
|--------|-------|
| External JS Files | $JS_FILES |
| Inline Scripts | $INLINE_COUNT |
| API Endpoints Found | $ENDPOINT_COUNT |
| Functions Extracted | $FUNC_COUNT |
| Potential Secrets | $KEY_COUNT |
| Source Maps | $MAP_COUNT |

## Output Files

### Raw Downloads
- \`raw/\` - Original JavaScript files (unmodified)

### Deobfuscated Code
- \`deobfuscated/\` - Readable JavaScript after deobfuscation
  - Use these files to understand site logic

### Extracted Logic
- \`extracted-logic/api-endpoints.txt\` - All discovered API calls
- \`extracted-logic/functions.txt\` - Function definitions found
- \`extracted-logic/potential-keys.txt\` - Possible API keys/tokens

### Source Maps
- \`source-maps/\` - Original source code (if .map files available)

## Key Findings

### API Endpoints
\`\`\`
$(head -20 "$OUTPUT_DIR/extracted-logic/api-endpoints.txt" 2>/dev/null || echo "No endpoints found")
\`\`\`

### Functions
\`\`\`
$(head -20 "$OUTPUT_DIR/extracted-logic/functions.txt" 2>/dev/null || echo "No functions found")
\`\`\`

### Potential Secrets (Review carefully)
\`\`\`
$(head -10 "$OUTPUT_DIR/extracted-logic/potential-keys.txt" 2>/dev/null || echo "No secrets found")
\`\`\`

## Next Steps

1. **Review deobfuscated code** in \`deobfuscated/\` folder
2. **Search for specific logic** (filtering, payment, auth)
3. **Analyze API calls** from \`extracted-logic/api-endpoints.txt\`
4. **Check source maps** if available in \`source-maps/\`
5. **Extract reusable patterns** for your own implementation

## Legal Note

This analysis is for **educational and reference purposes only**.
Only use extracted code from your own sites or with explicit authorization.

EOF

echo "Report generated: $OUTPUT_DIR/analysis/REPORT.md"
echo ""

# ============================================================================
# STEP 8: Create summary
# ============================================================================
echo "[8/8] Creating summary..."

TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | awk '{print $1}')

cat > "$OUTPUT_DIR/SUMMARY.txt" << EOF
DEEP CODE EXTRACTION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: $URL
Output: $OUTPUT_DIR
Total Size: $TOTAL_SIZE

EXTRACTION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • JavaScript Files: $JS_FILES external + $INLINE_COUNT inline
  • Deobfuscated: $PROCESSED files
  • API Endpoints: $ENDPOINT_COUNT
  • Functions: $FUNC_COUNT
  • Potential Secrets: $KEY_COUNT
  • Source Maps: $MAP_COUNT

 FOLDER STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  raw/                    Original JS files (unmodified)
  deobfuscated/           Readable JS (deobfuscated)
  source-maps/            Original source code (.map files)
  extracted-logic/
    ├── api-endpoints.txt All API calls found
    ├── functions.txt     Function definitions
    └── potential-keys.txt Possible API keys/tokens
  analysis/
    └── REPORT.md         Full analysis report

NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Open deobfuscated/ folder Browse readable JS
  2. Search for specific logic (grep "payment\|checkout\|filter")
  3. Review API endpoints from extracted-logic/
  4. Check REPORT.md for summary
  5. Extract reusable patterns for your project

USEFUL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Browse deobfuscated code
  code $OUTPUT_DIR/deobfuscated/

  # Find specific function
  grep -n "function checkout\|const checkout" $OUTPUT_DIR/deobfuscated/*.js

  # View all API endpoints
  cat $OUTPUT_DIR/extracted-logic/api-endpoints.txt

  # Check file sizes
  du -sh $OUTPUT_DIR/deobfuscated/*

  # Generate tree
  tree $OUTPUT_DIR -L 2

EOF

cat "$OUTPUT_DIR/SUMMARY.txt"

rm -f "$TEMP_HTML"

echo ""
echo "Deep code extraction complete!"
echo "All files saved to: $OUTPUT_DIR"
