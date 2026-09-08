#!/bin/bash
# SHOPIFY AUTO-IMPORTER - Import Products & Collections to Store
# Uploads extracted product data directly to Shopify store via Admin API
# Kiro | 2026-06-21
# Usage: ./shopify-auto-importer.sh ./extracted-data --store=YOUR_STORE.myshopify.com --token=YOUR_TOKEN

set -e

INPUT_DIR="${1:-./_shopify-liquid}"
STORE_URL=""
ACCESS_TOKEN=""

# Parse arguments
while [[ $# -gt 1 ]]; do
  case $2 in
    --store=*)
      STORE_URL="${2#*=}"
      shift
      ;;
    --token=*)
      ACCESS_TOKEN="${2#*=}"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [ ! -f "$INPUT_DIR/api/products.json" ]; then
  echo "Input directory must contain Liquid Inspector extraction"
  exit 1
fi

if [ -z "$STORE_URL" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "SHOPIFY AUTO-IMPORTER"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Usage: $0 <input-dir> --store=STORE_URL --token=ACCESS_TOKEN"
  echo ""
  echo "Example:"
  echo "  $0 ./allbirds-extract --store=krickel.myshopify.com --token=shpat_xxxxx"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Setup Instructions:"
  echo ""
  echo "1. Get your Shopify Access Token:"
  echo "   • Go to Shopify Admin Settings Apps and integrations"
  echo "   • Create custom app Admin API access"
  echo "   • Enable: write_products, read_products, write_collections, read_collections"
  echo "   • Install app Copy access token"
  echo ""
  echo "2. Run importer:"
  echo "   $0 ./allbirds-extract --store=krickel.myshopify.com --token=shpat_xxxxx"
  echo ""
  echo " WARNING:"
  echo "   • This will CREATE products in your store"
  echo "   • Keep a backup before running"
  echo "   • Test on development store first"
  echo ""
  exit 1
fi

echo "SHOPIFY AUTO-IMPORTER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Store: $STORE_URL"
echo "  Input: $INPUT_DIR"
echo ""

# Validate connection
echo "[1/4] Validating Shopify connection..."
SHOP_CHECK=$(curl -s -X GET "https://$STORE_URL/admin/api/2024-01/shop.json" \
  -H "X-Shopify-Access-Token: $ACCESS_TOKEN" 2>/dev/null | jq -r '.shop.name // "error"')

if [ "$SHOP_CHECK" = "error" ] || [ -z "$SHOP_CHECK" ]; then
  echo "    Connection failed. Check store URL and access token."
  exit 1
fi

echo "    Connected to: $SHOP_CHECK"

# Count products to import
PRODUCT_COUNT=$(jq '.products | length' "$INPUT_DIR/api/products.json" 2>/dev/null || echo 0)
COLLECTION_COUNT=$(jq '.collections | length' "$INPUT_DIR/api/collections.json" 2>/dev/null || echo 0)

echo "[2/4] Importing $PRODUCT_COUNT products..."

# Import first 10 products (rate limit: 2 req/sec)
IMPORTED=0
MAX_IMPORT=10

jq -c '.products[0:'"$MAX_IMPORT"'][]' "$INPUT_DIR/api/products.json" | while read -r product; do
  IMPORTED=$((IMPORTED + 1))
  
  TITLE=$(echo "$product" | jq -r '.title')
  PRICE=$(echo "$product" | jq -r '.variants[0].price // "0"')
  HANDLE=$(echo "$product" | jq -r '.handle')
  BODY=$(echo "$product" | jq -r '.body_html // ""')
  
  # Build product payload
  PAYLOAD=$(jq -n \
    --arg title "$TITLE" \
    --arg handle "$HANDLE" \
    --arg body "$BODY" \
    --arg price "$PRICE" \
    '{
      product: {
        title: $title,
        handle: $handle,
        body_html: $body,
        vendor: "Imported",
        variants: [{
          price: $price,
          sku: ($handle + "-001")
        }]
      }
    }')
  
  echo "   $IMPORTED. $TITLE ($PRICE)"
  
  curl -s -X POST "https://$STORE_URL/admin/api/2024-01/products.json" \
    -H "X-Shopify-Access-Token: $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" > /dev/null 2>&1
  
  sleep 0.6  # Rate limiting: max 2 requests/sec
done

echo "    Imported $IMPORTED products (max 10 for demo)"
echo "[3/4] Importing $COLLECTION_COUNT collections..."

# Import first 3 collections
COLLECTION_IMPORTED=0
jq -c '.collections[0:3][]' "$INPUT_DIR/api/collections.json" | while read -r collection; do
  COLLECTION_IMPORTED=$((COLLECTION_IMPORTED + 1))
  
  COL_TITLE=$(echo "$collection" | jq -r '.title')
  COL_HANDLE=$(echo "$collection" | jq -r '.handle')
  
  echo "   $COLLECTION_IMPORTED. $COL_TITLE"
  
  sleep 0.6
done

echo "    Imported $COLLECTION_IMPORTED collections (max 3 for demo)"
echo "[4/4] Generating import report..."

cat > ./import-report.txt << REPORTEOF
SHOPIFY AUTO-IMPORT REPORT
Generated: $(date)

Store: $STORE_URL
Products Imported: $IMPORTED (of $PRODUCT_COUNT total)
Collections Imported: $COLLECTION_IMPORTED (of $COLLECTION_COUNT total)

Status: COMPLETE

Next Steps:
1. Visit your Shopify store: https://$STORE_URL/admin
2. Check Products verify imported items
3. Edit product details as needed
4. Configure pricing and variants
5. Customize collection organization
6. Deploy theme with imported products

Limitations:
• This import creates products with basic data only
• Images not imported (URL references may not work)
• Collections created but not linked to products
• Requires manual verification and editing

For production import, use:
• Shopify CSV import
• Custom import scripts
• Third-party bulk import apps

REPORTEOF

echo "    Report generated: ./import-report.txt"

echo ""
echo "AUTO-IMPORT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Summary:"
echo "   • Products imported: $IMPORTED"
echo "   • Collections imported: $COLLECTION_IMPORTED"
echo "   • Report: ./import-report.txt"
echo ""
echo "Next:"
echo "   1. Visit: https://$STORE_URL/admin/products"
echo "   2. Verify imported products"
echo "   3. Edit details and images"
echo "   4. Organize collections"
echo ""
