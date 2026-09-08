#!/bin/bash
# WEB CLONE GENERATOR - Generate Working Website from Shopify Extraction
# Takes Liquid Inspector output, generates standalone HTML clone
# Kiro | 2026-06-21
# Usage: ./web-clone-generator.sh ./extracted-data ./output-website

set -e

INPUT_DIR="${1:-./_shopify-liquid}"
OUTPUT_DIR="${2:-./_website-clone}"

if [ ! -f "$INPUT_DIR/api/products.json" ]; then
  echo "Input directory must contain Liquid Inspector extraction"
  echo "   (needs: api/products.json, api/collections.json, theme-metadata.json)"
  exit 1
fi

echo "WEB CLONE GENERATOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Input: $INPUT_DIR"
echo "  Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR/assets" "$OUTPUT_DIR/data"

# Extract metadata
THEME_NAME=$(jq -r '.name // "Store"' "$INPUT_DIR/theme-metadata.json" 2>/dev/null || echo "Store")
PRODUCT_COUNT=$(jq '.products | length' "$INPUT_DIR/api/products.json" 2>/dev/null || echo 0)
COLLECTION_COUNT=$(jq '.collections | length' "$INPUT_DIR/api/collections.json" 2>/dev/null || echo 0)

echo "[1/3] Preparing data files..."
cp "$INPUT_DIR/api/products.json" "$OUTPUT_DIR/data/products.json"
cp "$INPUT_DIR/api/collections.json" "$OUTPUT_DIR/data/collections.json"
echo "    $PRODUCT_COUNT products + $COLLECTION_COUNT collections"

echo "[2/3] Downloading theme CSS files..."
ASSETS_DOWNLOADED=0
if [ -f "$INPUT_DIR/asset-urls.txt" ]; then
  while IFS= read -r asset_url && [ $ASSETS_DOWNLOADED -lt 5 ]; do
    if [[ "$asset_url" == *.css ]]; then
      filename=$(basename "$asset_url" | cut -d'?' -f1)
      echo "   $filename"
      timeout 5 curl -s "https:$asset_url" -o "$OUTPUT_DIR/assets/$filename" 2>/dev/null || true
      ASSETS_DOWNLOADED=$((ASSETS_DOWNLOADED + 1))
    fi
  done < "$INPUT_DIR/asset-urls.txt"
fi
echo "    Downloaded $ASSETS_DOWNLOADED CSS files"

echo "[3/3] Generating HTML clone..."

# Generate main HTML file
cat > "$OUTPUT_DIR/index.html" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title id="storeTitle">Store</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: #f8f9fa;
      color: #333;
      line-height: 1.6;
    }

    header {
      background: white;
      border-bottom: 1px solid #e5e5e5;
      padding: 1rem 2rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      sticky: top;
    }

    header h1 {
      font-size: 1.5rem;
      margin-bottom: 1rem;
      color: #000;
    }

    .header-controls {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .header-controls select,
    .header-controls input {
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 0.9rem;
    }

    .header-controls input {
      min-width: 200px;
    }

    .container {
      max-width: 1200px;
      margin: 2rem auto;
      padding: 0 1rem;
    }

    .stats {
      background: white;
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 2rem;
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stat {
      flex: 1;
      min-width: 150px;
    }

    .stat-label {
      font-size: 0.9rem;
      color: #666;
      margin-bottom: 0.5rem;
    }

    .stat-value {
      font-size: 1.8rem;
      font-weight: bold;
      color: #000;
    }

    .filters {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      margin-bottom: 2rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .filter-group {
      margin-bottom: 1rem;
    }

    .filter-group label {
      display: block;
      font-weight: 500;
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
    }

    .filter-group select {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
    }

    .products-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
    }

    .product-card {
      background: white;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      transition: transform 0.2s, box-shadow 0.2s;
      cursor: pointer;
    }

    .product-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .product-image {
      width: 100%;
      height: 200px;
      background: #f0f0f0;
      object-fit: cover;
      display: block;
    }

    .product-info {
      padding: 1rem;
    }

    .product-title {
      font-weight: 600;
      font-size: 0.95rem;
      margin-bottom: 0.5rem;
      color: #000;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .product-price {
      font-size: 1.1rem;
      font-weight: bold;
      color: #2c5282;
      margin-bottom: 0.5rem;
    }

    .product-compare {
      font-size: 0.85rem;
      color: #999;
      text-decoration: line-through;
    }

    .product-variants {
      font-size: 0.8rem;
      color: #666;
      margin-top: 0.5rem;
    }

    .loading {
      text-align: center;
      padding: 2rem;
      color: #666;
    }

    .empty {
      text-align: center;
      padding: 3rem;
      color: #999;
      background: white;
      border-radius: 8px;
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: #666;
      font-size: 0.85rem;
      margin-top: 3rem;
    }

    @media (max-width: 768px) {
      .products-grid {
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      }

      header {
        padding: 1rem;
      }

      .stats {
        flex-direction: column;
        gap: 1rem;
      }

      .header-controls {
        flex-direction: column;
      }

      .header-controls input {
        min-width: auto;
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1 id="storeName">Loading Store...</h1>
    <div class="header-controls">
      <input type="text" id="searchInput" placeholder="Search products...">
      <select id="collectionFilter">
        <option value="">All Collections</option>
      </select>
      <select id="sortBy">
        <option value="name">Sort by Name</option>
        <option value="price-low">Price: Low to High</option>
        <option value="price-high">Price: High to Low</option>
      </select>
    </div>
  </header>

  <div class="container">
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Total Products</div>
        <div class="stat-value" id="totalProducts">0</div>
      </div>
      <div class="stat">
        <div class="stat-label">Collections</div>
        <div class="stat-value" id="totalCollections">0</div>
      </div>
      <div class="stat">
        <div class="stat-label">Avg Price</div>
        <div class="stat-value" id="avgPrice">$0</div>
      </div>
      <div class="stat">
        <div class="stat-label">Price Range</div>
        <div class="stat-value" id="priceRange">-</div>
      </div>
    </div>

    <div class="filters">
      <div class="filter-group">
        <label>Variants Filter</label>
        <select id="variantFilter">
          <option value="">All</option>
          <option value="1">Single Variant</option>
          <option value="2+">2+ Variants</option>
        </select>
      </div>
    </div>

    <div id="products" class="products-grid">
      <div class="loading">Loading products...</div>
    </div>

    <div class="footer">
      <p>Web Clone Generated | Theme Inspector v3 | All data from public Shopify APIs</p>
      <p id="generatedTime"></p>
    </div>
  </div>

  <script>
    // Data storage
    let allProducts = [];
    let allCollections = [];
    let filteredProducts = [];

    // Load data
    async function loadData() {
      try {
        const productsRes = await fetch('./data/products.json');
        const collectionsRes = await fetch('./data/collections.json');
        
        allProducts = (await productsRes.json()).products || [];
        allCollections = (await collectionsRes.json()).collections || [];

        renderUI();
      } catch (err) {
        console.error('Error loading data:', err);
        document.getElementById('products').innerHTML = '<div class="empty">Error loading data</div>';
      }
    }

    function renderUI() {
      renderStats();
      renderCollectionFilter();
      renderProducts(allProducts);
      document.getElementById('generatedTime').textContent = new Date().toLocaleString();
    }

    function renderStats() {
      const prices = allProducts.flatMap(p => p.variants.map(v => parseFloat(v.price) || 0));
      const avgPrice = prices.length ? (prices.reduce((a, b) => a + b) / prices.length).toFixed(2) : 0;
      const minPrice = prices.length ? Math.min(...prices).toFixed(2) : 0;
      const maxPrice = prices.length ? Math.max(...prices).toFixed(2) : 0;

      document.getElementById('totalProducts').textContent = allProducts.length;
      document.getElementById('totalCollections').textContent = allCollections.length;
      document.getElementById('avgPrice').textContent = `$${avgPrice}`;
      document.getElementById('priceRange').textContent = `$${minPrice} - $${maxPrice}`;
    }

    function renderCollectionFilter() {
      const select = document.getElementById('collectionFilter');
      allCollections.forEach(col => {
        const option = document.createElement('option');
        option.value = col.handle;
        option.textContent = `${col.title} (${col.product_count || 0})`;
        select.appendChild(option);
      });
    }

    function renderProducts(products) {
      if (!products.length) {
        document.getElementById('products').innerHTML = '<div class="empty">No products found</div>';
        return;
      }

      const html = products.map(product => `
        <div class="product-card" data-handle="${product.handle}">
          ${product.images.length ? `<img src="${product.images[0].src}" alt="${product.title}" class="product-image">` : '<div class="product-image"></div>'}
          <div class="product-info">
            <div class="product-title" title="${product.title}">${product.title}</div>
            <div class="product-price">$${product.variants[0]?.price || 'N/A'}</div>
            ${product.variants[0]?.compare_at_price ? `<div class="product-compare">Was $${product.variants[0].compare_at_price}</div>` : ''}
            <div class="product-variants">${product.variants.length} variant${product.variants.length !== 1 ? 's' : ''}</div>
          </div>
        </div>
      `).join('');

      document.getElementById('products').innerHTML = html;
    }

    // Filter handlers
    document.getElementById('searchInput').addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      filteredProducts = allProducts.filter(p => p.title.toLowerCase().includes(query));
      renderProducts(filteredProducts);
    });

    document.getElementById('collectionFilter').addEventListener('change', (e) => {
      if (!e.target.value) {
        renderProducts(allProducts);
      } else {
        filteredProducts = allProducts.filter(p => p.collections?.includes(e.target.value));
        renderProducts(filteredProducts);
      }
    });

    document.getElementById('sortBy').addEventListener('change', (e) => {
      const toSort = filteredProducts.length ? filteredProducts : allProducts;
      switch (e.target.value) {
        case 'price-low':
          toSort.sort((a, b) => (parseFloat(a.variants[0]?.price) || 0) - (parseFloat(b.variants[0]?.price) || 0));
          break;
        case 'price-high':
          toSort.sort((a, b) => (parseFloat(b.variants[0]?.price) || 0) - (parseFloat(a.variants[0]?.price) || 0));
          break;
        case 'name':
        default:
          toSort.sort((a, b) => a.title.localeCompare(b.title));
      }
      renderProducts(toSort);
    });

    document.getElementById('variantFilter').addEventListener('change', (e) => {
      let filtered = allProducts;
      if (e.target.value === '1') {
        filtered = allProducts.filter(p => p.variants.length === 1);
      } else if (e.target.value === '2+') {
        filtered = allProducts.filter(p => p.variants.length >= 2);
      }
      renderProducts(filtered);
    });

    // Load on startup
    loadData();
  </script>
</body>
</html>
HTMLEOF

echo "    Generated index.html"

echo ""
echo "WEB CLONE GENERATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Output: $OUTPUT_DIR"
echo ""
echo "Files:"
echo "   • index.html - Standalone website clone"
echo "   • data/products.json - Product data"
echo "   • data/collections.json - Collections data"
echo "   • assets/ - CSS files (if downloaded)"
echo ""
echo "Usage:"
echo "   # Serve locally"
echo "   cd $OUTPUT_DIR && python3 -m http.server 8000"
echo "   # Then open: http://localhost:8000"
echo ""
echo "Features:"
echo "   Search products by name"
echo "   Filter by collection"
echo "   Sort by price/name"
echo "   Show pricing & variants"
echo "   Responsive design"
echo "   Stats dashboard"
echo ""
echo "Next: Import to Lovable or deploy as static site"
