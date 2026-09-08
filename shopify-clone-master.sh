#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# SHOPIFY CLONE MASTER - Ultimate Shopify Theme Cloning Toolkit
# Unified tool combining all 6 extraction + analysis modules
# Kiro | 2026-06-21 | v3.0
#
# Usage: ./shopify-clone-master.sh <command> [args]
#
# Commands:
#   extract <url> <output>     Extract all data from Shopify store
#   analyze <input> <output>   Run all 6 analyzers on extracted data
#   clone <url> <output>       Full clone: extract + analyze + generate
#   compare <store1> <store2>  Compare multiple stores side-by-side
#   theme <input> <output>     Generate Shopify Liquid theme from extraction
#   web <input> <output>       Generate standalone HTML website clone
#   import <input> --store=    Import products to Shopify store
#   all <url> <output>         DO EVERYTHING (extract + analyze + theme + web)
# ═══════════════════════════════════════════════════════════════════

set -e

# Tool directory
TOOL_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  SHOPIFY CLONE MASTER v3.0 - Ultimate Cloning Toolkit        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_usage() {
    print_header
    cat << 'USAGE'
Commands:

  extract <url> <output>
      Extract all data from a Shopify store (products, collections, theme, HTML)

  analyze <input> <output>
      Run ALL 6 analyzers on extracted data:
      1. Smart Section Reverse-Engineer reconstruct .liquid sections
      2. CSS/Style Cloner extract design system, generate theme.css
      3. JS Logic Extractor extract functions, cart logic, variant handlers
      4. Cart Flow Mapper trace AJAX endpoints, payment methods, flow diagram
      5. Product Schema Analyzer pricing tiers, variant matrix, metafields
      6. (Multi-Store Comparator - use 'compare' command separately)

  clone <url> <output>
      Full clone: extract + analyze + generate theme + generate website

  compare <store1> <store2> [store3] [store4]
      Compare multiple stores side-by-side (dashboard + CSV + rankings)

  theme <input> <output>
      Generate Shopify Liquid theme from extraction

  web <input> <output>
      Generate standalone HTML website clone

  import <input> --store=URL --token=TOKEN
      Import products to Shopify store via Admin API

  all <url> <output>
      DO EVERYTHING: extract + analyze + theme + web + flow + styles + JS

Examples:

  # Extract competitor data
  ./shopify-clone-master.sh extract https://rothys.com ./rothys-data

  # Run all analyzers
  ./shopify-clone-master.sh analyze ./rothys-data ./rothys-analysis

  # Full clone (everything)
  ./shopify-clone-master.sh clone https://rothys.com ./rothys-clone

  # Compare 3 stores
  ./shopify-clone-master.sh compare allbirds.com rothys.com taylorstitch.com

  # Generate Liquid theme
  ./shopify-clone-master.sh theme ./rothys-data ./my-theme

  # Generate HTML website
  ./shopify-clone-master.sh web ./rothys-data ./my-website

USAGE
}

# ═══════════════════════════════════════════════════════════════════
# EXTRACT - Run Liquid Inspector
# ═══════════════════════════════════════════════════════════════════

cmd_extract() {
    local url="$1"
    local output="$2"
    
    if [ -z "$url" ] || [ -z "$output" ]; then
        echo -e "${RED}Usage: extract <url> <output>${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Phase 1: Extracting data from $url${NC}"
    "$TOOL_DIR/shopify-liquid-inspector.sh" "$url" "$output"
    echo -e "${GREEN}Extraction complete: $output${NC}"
}

# ═══════════════════════════════════════════════════════════════════
# ANALYZE - Run all 6 analyzers
# ═══════════════════════════════════════════════════════════════════

cmd_analyze() {
    local input="$1"
    local output="$2"
    
    if [ -z "$input" ] || [ -z "$output" ]; then
        echo -e "${RED}Usage: analyze <input> <output>${NC}"
        exit 1
    fi
    
    mkdir -p "$output"
    
    echo -e "${BLUE}Phase 1: Smart Section Reverse-Engineer${NC}"
    python3 "$TOOL_DIR/section-reverse-engineer.py" "$input" "$output/sections"
    echo ""
    
    echo -e "${BLUE}Phase 2: CSS/Style Cloner${NC}"
    python3 "$TOOL_DIR/css-style-cloner.py" "$input" "$output/styles"
    echo ""
    
    echo -e "${BLUE}Phase 3: JS Logic Extractor${NC}"
    python3 "$TOOL_DIR/js-logic-extractor.py" "$input" "$output/js-logic"
    echo ""
    
    echo -e "${BLUE}Phase 4: Cart Flow Mapper${NC}"
    python3 "$TOOL_DIR/cart-flow-mapper.py" "$input" "$output/cart-flow"
    echo ""
    
    echo -e "${BLUE}Phase 5: Product Schema Analyzer${NC}"
    python3 "$TOOL_DIR/product-schema-analyzer.py" "$input" "$output/products"
    echo ""
    
    echo -e "${GREEN}ALL 6 ANALYZERS COMPLETE${NC}"
    echo -e "${CYAN}Output: $output/${NC}"
    echo "   • sections/ - Reconstructed .liquid section files"
    echo "   • styles/ - theme.css, settings_schema.json, design-system.json"
    echo "   • js-logic/ - Functions, cart logic, selectCallback, app detection"
    echo "   • cart-flow/ - Flow diagram, AJAX endpoints, payment methods"
    echo "   • products/ - Pricing tiers, variant matrix, metafields"
}

# ═══════════════════════════════════════════════════════════════════
# CLONE - Extract + Analyze + Generate
# ═══════════════════════════════════════════════════════════════════

cmd_clone() {
    local url="$1"
    local output="$2"
    
    if [ -z "$url" ] || [ -z "$output" ]; then
        echo -e "${RED}Usage: clone <url> <output>${NC}"
        exit 1
    fi
    
    print_header
    echo -e "${YELLOW}FULL CLONE: $url $output${NC}"
    echo ""
    
    # Phase 1: Extract
    cmd_extract "$url" "$output/extracted"
    echo ""
    
    # Phase 2: Analyze
    cmd_analyze "$output/extracted" "$output/analysis"
    echo ""
    
    # Phase 3: Generate theme
    echo -e "${BLUE}Phase 3: Generating Liquid theme${NC}"
    "$TOOL_DIR/shopify-theme-converter.sh" "$output/extracted" "$output/theme"
    echo ""
    
    # Phase 4: Generate website
    echo -e "${BLUE}Phase 4: Generating HTML website${NC}"
    "$TOOL_DIR/web-clone-generator.sh" "$output/extracted" "$output/website"
    echo ""
    
    # Summary
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              FULL CLONE COMPLETE                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Output: $output/${NC}"
    echo "   • extracted/ - Raw data (products, collections, HTML, metadata)"
    echo "   • analysis/ - All 6 analyzer outputs"
    echo "     ├── sections/ - .liquid section files"
    echo "     ├── styles/ - theme.css + settings_schema.json"
    echo "     ├── js-logic/ - Functions, cart logic, app detection"
    echo "     ├── cart-flow/ - Flow diagram + payment methods"
    echo "     └── products/ - Pricing intelligence + variant matrix"
    echo "   • theme/ - Production-ready Shopify Liquid theme"
    echo "   • website/ - Standalone HTML website clone"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "   1. cd $output/website && python3 -m http.server 8000"
    echo "   2. shopify theme dev --store=YOUR_STORE.myshopify.com --path=$output/theme"
}

# ═══════════════════════════════════════════════════════════════════
# COMPARE - Multi-store comparator
# ═══════════════════════════════════════════════════════════════════

cmd_compare() {
    if [ $# -lt 2 ]; then
        echo -e "${RED}Usage: compare <store1> <store2> [store3] ...${NC}"
        exit 1
    fi
    
    python3 "$TOOL_DIR/multi-store-comparator.py" "$@"
}

# ═══════════════════════════════════════════════════════════════════
# THEME - Generate Liquid theme
# ═══════════════════════════════════════════════════════════════════

cmd_theme() {
    local input="$1"
    local output="$2"
    
    if [ -z "$input" ] || [ -z "$output" ]; then
        echo -e "${RED}Usage: theme <input> <output>${NC}"
        exit 1
    fi
    
    "$TOOL_DIR/shopify-theme-converter.sh" "$input" "$output"
}

# ═══════════════════════════════════════════════════════════════════
# WEB - Generate HTML website
# ═══════════════════════════════════════════════════════════════════

cmd_web() {
    local input="$1"
    local output="$2"
    
    if [ -z "$input" ] || [ -z "$output" ]; then
        echo -e "${RED}Usage: web <input> <output>${NC}"
        exit 1
    fi
    
    "$TOOL_DIR/web-clone-generator.sh" "$input" "$output"
}

# ═══════════════════════════════════════════════════════════════════
# IMPORT - Import products to store
# ═══════════════════════════════════════════════════════════════════

cmd_import() {
    if [ $# -lt 2 ]; then
        echo -e "${RED}Usage: import <input> --store=URL --token=TOKEN${NC}"
        exit 1
    fi
    
    "$TOOL_DIR/shopify-auto-importer.sh" "$@"
}

# ═══════════════════════════════════════════════════════════════════
# ALL - Do everything
# ═══════════════════════════════════════════════════════════════════

cmd_all() {
    cmd_clone "$@"
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

command="$1"
shift

case "$command" in
    extract)  cmd_extract "$@" ;;
    analyze)  cmd_analyze "$@" ;;
    clone)    cmd_clone "$@" ;;
    compare)  cmd_compare "$@" ;;
    theme)    cmd_theme "$@" ;;
    web)      cmd_web "$@" ;;
    import)   cmd_import "$@" ;;
    all)      cmd_all "$@" ;;
    help|-h|--help) print_usage ;;
    *)
        echo -e "${RED}Unknown command: $command${NC}"
        print_usage
        exit 1
        ;;
esac
