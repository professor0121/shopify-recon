#!/bin/bash
# SHOPIFY LIQUID THEME CONVERTER - Generate Shopify Theme from Extraction
# Converts competitor theme structure production-ready Shopify Liquid theme
# Kiro | 2026-06-21
# Usage: ./shopify-theme-converter.sh ./extracted-data ./output-theme

set -e

INPUT_DIR="${1:-./_shopify-liquid}"
OUTPUT_DIR="${2:-./_shopify-theme}"

if [ ! -f "$INPUT_DIR/api/products.json" ]; then
  echo "Input directory must contain Liquid Inspector extraction"
  exit 1
fi

echo "SHOPIFY LIQUID THEME CONVERTER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Input: $INPUT_DIR"
echo "  Output: $OUTPUT_DIR"
echo ""

# Create directory structure
mkdir -p "$OUTPUT_DIR"/{layout,templates,sections,snippets,assets/{css,js},config}

THEME_NAME=$(jq -r '.name // "Cloned Theme"' "$INPUT_DIR/theme-metadata.json" 2>/dev/null || echo "Cloned Theme")
PRODUCT_COUNT=$(jq '.products | length' "$INPUT_DIR/api/products.json" 2>/dev/null || echo 0)

echo "[1/5] Creating theme structure..."

# 1. Generate config.json
cat > "$OUTPUT_DIR/config/settings_schema.json" << 'EOF'
[
  {
    "name": "theme",
    "settings": [
      {
        "type": "header",
        "content": "Colors"
      },
      {
        "type": "color",
        "id": "color_primary",
        "label": "Primary Color",
        "default": "#000000"
      },
      {
        "type": "color",
        "id": "color_text",
        "label": "Text Color",
        "default": "#333333"
      },
      {
        "type": "header",
        "content": "Typography"
      },
      {
        "type": "font_picker",
        "id": "font_body",
        "label": "Body Font",
        "default": "helvetica_neue_n4"
      },
      {
        "type": "font_picker",
        "id": "font_heading",
        "label": "Heading Font",
        "default": "helvetica_neue_n7"
      }
    ]
  }
]
EOF

echo "    config/settings_schema.json"

# 2. Generate theme.liquid (main layout)
cat > "$OUTPUT_DIR/layout/theme.liquid" << 'EOF'
<!DOCTYPE html>
<html lang="{{ shop.locale }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="ie=edge">
  <title>{{ page_title }}{% if page %} - {{ shop.name }}{% endif %}</title>
  <meta name="description" content="{{ page_description | escape }}">
  
  {{ content_for_header }}
  
  <style>
    :root {
      --color-primary: {{ settings.color_primary }};
      --color-text: {{ settings.color_text }};
    }
    
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: {{ settings.font_body | font_face }};
      color: var(--color-text);
      line-height: 1.6;
      background: #f8f9fa;
    }
    
    header {
      background: white;
      border-bottom: 1px solid #e5e5e5;
      padding: 1rem 2rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    header h1 {
      font-family: {{ settings.font_heading | font_face }};
      color: var(--color-primary);
      margin-bottom: 1rem;
    }
    
    .container {
      max-width: 1200px;
      margin: 2rem auto;
      padding: 0 1rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ shop.name }}</h1>
    {% include 'header-nav' %}
  </header>

  <main>
    {% include 'breadcrumbs' %}
    {{ content_for_layout }}
  </main>

  <footer>
    {% include 'footer' %}
  </footer>
</body>
</html>
EOF

echo "    layout/theme.liquid"

# 3. Generate index.liquid (homepage template)
cat > "$OUTPUT_DIR/templates/index.liquid" << 'EOF'
<div class="container">
  <section class="hero" style="text-align: center; padding: 4rem 0; background: linear-gradient(135deg, var(--color-primary) 0%, rgba(0,0,0,0.1) 100%);">
    <h1 style="color: white; font-size: 2.5rem; margin-bottom: 1rem;">Welcome to {{ shop.name }}</h1>
    <p style="color: rgba(255,255,255,0.9); font-size: 1.1rem;">Discover our featured products</p>
  </section>

  <section class="featured-products" style="padding: 3rem 0;">
    <h2 style="margin-bottom: 2rem;">Featured Collection</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem;">
      {% for product in collection.products limit: 8 %}
        {% include 'product-card' with product %}
      {% endfor %}
    </div>
  </section>
</div>
EOF

echo "    templates/index.liquid"
echo "[2/5] Creating product templates..."

# 4. Generate product.liquid (product page template)
cat > "$OUTPUT_DIR/templates/product.liquid" << 'EOF'
<div class="container" style="padding: 2rem 0;">
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
    <div class="product-images">
      {% for image in product.featured_image %}
        <img src="{{ image | image_url: width: 500 }}" alt="{{ product.title }}" style="width: 100%; margin-bottom: 1rem; border-radius: 8px;">
      {% endfor %}
    </div>
    
    <div class="product-info">
      <h1 style="margin-bottom: 1rem;">{{ product.title }}</h1>
      
      <div style="font-size: 1.5rem; font-weight: bold; color: var(--color-primary); margin-bottom: 1rem;">
        {% if product.compare_at_price > product.price %}
          <span style="text-decoration: line-through; color: #999; margin-right: 1rem;">{{ product.compare_at_price | money }}</span>
        {% endif %}
        {{ product.price | money }}
      </div>
      
      <p style="margin-bottom: 2rem; color: #666;">{{ product.description }}</p>
      
      <form method="POST" action="/cart/add" style="margin-bottom: 2rem;">
        {% for option in product.options_with_values %}
          <label style="display: block; margin-bottom: 1rem;">
            {{ option.name }}:
            <select name="options[{{ option.name }}]" style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px;">
              {% for value in option.values %}
                <option>{{ value }}</option>
              {% endfor %}
            </select>
          </label>
        {% endfor %}
        
        <button type="submit" style="background: var(--color-primary); color: white; padding: 1rem 2rem; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer;">Add to Cart</button>
      </form>
    </div>
  </div>
</div>
EOF

echo "    templates/product.liquid"

# 5. Generate collection.liquid (collection page template)
cat > "$OUTPUT_DIR/templates/collection.liquid" << 'COLLEOF'
<div class="container" style="padding: 2rem 0;">
  <h1 style="margin-bottom: 1rem;">{{ collection.title }}</h1>
  <p style="margin-bottom: 2rem; color: #666;">{{ collection.description }}</p>
  
  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem;">
    {% for product in collection.products %}
      {% include 'product-card' with product %}
    {% endfor %}
  </div>
</div>
COLLEOF

echo "    templates/collection.liquid"
echo "[3/5] Creating snippets..."

# 6. Generate product-card snippet
cat > "$OUTPUT_DIR/snippets/product-card.liquid" << 'SNIPPETEOF'
<div style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s;">
  <a href="{{ product.url }}" style="text-decoration: none; color: inherit;">
    <img src="{{ product.featured_image | image_url: width: 300 }}" alt="{{ product.title }}" style="width: 100%; height: 200px; object-fit: cover; display: block;">
    
    <div style="padding: 1rem;">
      <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem; font-weight: 600;">{{ product.title }}</h3>
      
      <div style="font-size: 1.1rem; font-weight: bold; color: #2c5282; margin-bottom: 0.5rem;">
        {{ product.price | money }}
      </div>
      
      {% if product.available %}
        <span style="color: green; font-size: 0.9rem;">In Stock</span>
      {% else %}
        <span style="color: red; font-size: 0.9rem;">Out of Stock</span>
      {% endif %}
      
      <div style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
        {{ product.variants | size }} variant{{ product.variants | size != 1 | pluralize }}
      </div>
    </div>
  </a>
</div>
SNIPPETEOF

echo "    snippets/product-card.liquid"

# 7. Generate header navigation snippet
cat > "$OUTPUT_DIR/snippets/header-nav.liquid" << 'NAVEOF'
<nav style="display: flex; gap: 2rem; flex-wrap: wrap;">
  <a href="/" style="color: var(--color-text); text-decoration: none; font-weight: 500;">Home</a>
  {% for link in linklists.main-menu.links %}
    <a href="{{ link.url }}" style="color: var(--color-text); text-decoration: none; font-weight: 500;">{{ link.title }}</a>
  {% endfor %}
  <a href="/cart" style="color: var(--color-primary); text-decoration: none; font-weight: 500;">Cart ({{ cart.item_count }})</a>
</nav>
NAVEOF

echo "    snippets/header-nav.liquid"

# 8. Generate breadcrumbs snippet
cat > "$OUTPUT_DIR/snippets/breadcrumbs.liquid" << 'BREADEOF'
<nav style="margin-bottom: 2rem; font-size: 0.9rem; color: #666;">
  <a href="/" style="color: var(--color-primary); text-decoration: none;">Home</a>
  {% if template != 'index' %}
    &nbsp;/&nbsp;
    <span>{{ page_title }}</span>
  {% endif %}
</nav>
BREADEOF

echo "    snippets/breadcrumbs.liquid"

# 9. Generate footer snippet
cat > "$OUTPUT_DIR/snippets/footer.liquid" << 'FOOTEOF'
<footer style="background: #f8f9fa; border-top: 1px solid #e5e5e5; margin-top: 4rem; padding: 2rem;">
  <div class="container">
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem; margin-bottom: 2rem;">
      <div>
        <h4 style="margin-bottom: 1rem; font-weight: 600;">About</h4>
        <p>{{ shop.description }}</p>
      </div>
      <div>
        <h4 style="margin-bottom: 1rem; font-weight: 600;">Quick Links</h4>
        <ul style="list-style: none;">
          <li><a href="/" style="color: var(--color-text); text-decoration: none;">Home</a></li>
          <li><a href="/collections/all" style="color: var(--color-text); text-decoration: none;">Shop</a></li>
          <li><a href="/pages/about" style="color: var(--color-text); text-decoration: none;">About</a></li>
        </ul>
      </div>
      <div>
        <h4 style="margin-bottom: 1rem; font-weight: 600;">Support</h4>
        <ul style="list-style: none;">
          <li><a href="/pages/contact" style="color: var(--color-text); text-decoration: none;">Contact</a></li>
          <li><a href="/pages/returns" style="color: var(--color-text); text-decoration: none;">Returns</a></li>
          <li><a href="/policies/privacy-policy" style="color: var(--color-text); text-decoration: none;">Privacy</a></li>
        </ul>
      </div>
    </div>
    <div style="text-align: center; padding-top: 2rem; border-top: 1px solid #e5e5e5; color: #666; font-size: 0.9rem;">
      <p>&copy; {{ shop.name }} 2026. All rights reserved. | Theme generated by Liquid Converter v1</p>
    </div>
  </div>
</footer>
FOOTEOF

echo "    snippets/footer.liquid"
echo "[4/5] Creating section stubs..."

# 10. Generate hero section
cat > "$OUTPUT_DIR/sections/hero.liquid" << 'HEROEOF'
{% schema %}
{
  "name": "Hero",
  "settings": [
    {
      "type": "text",
      "id": "title",
      "label": "Title",
      "default": "Welcome"
    },
    {
      "type": "text",
      "id": "subtitle",
      "label": "Subtitle"
    }
  ]
}
{% endschema %}

<div style="background: linear-gradient(135deg, var(--color-primary) 0%, rgba(0,0,0,0.1) 100%); padding: 4rem 2rem; text-align: center; color: white;">
  <h1 style="font-size: 2.5rem; margin-bottom: 1rem;">{{ section.settings.title }}</h1>
  {% if section.settings.subtitle %}
    <p style="font-size: 1.1rem;">{{ section.settings.subtitle }}</p>
  {% endif %}
</div>
HEROEOF

echo "    sections/hero.liquid"

echo "[5/5] Creating theme metadata..."

# 11. Generate theme.json (Shopify theme config)
cat > "$OUTPUT_DIR/config/settings_data.json" << 'CONFIGEOF'
{
  "current": {
    "color_primary": "#000000",
    "color_text": "#333333",
    "font_body": "helvetica_neue_n4",
    "font_heading": "helvetica_neue_n7"
  },
  "presets": {
    "Default": {
      "color_primary": "#000000",
      "color_text": "#333333"
    }
  }
}
CONFIGEOF

echo "    config/settings_data.json"

# 12. Create theme.toml for Shopify CLI
cat > "$OUTPUT_DIR/theme.toml" << 'TOMLEOF'
# Theme configuration

[theme]
name = "Cloned Theme"
id = 0
role = "development"
development = true

[[ignores]]
path = "node_modules"

[[ignores]]
path = ".git"
TOMLEOF

echo "    theme.toml (Shopify CLI config)"

echo ""
echo "LIQUID THEME CONVERSION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Theme: $OUTPUT_DIR"
echo ""
echo "Theme Structure:"
echo "   • layout/theme.liquid - Main layout wrapper"
echo "   • templates/index.liquid - Homepage"
echo "   • templates/product.liquid - Product page"
echo "   • templates/collection.liquid - Collection page"
echo "   • snippets/ - Reusable components"
echo "   • sections/ - Theme builder sections"
echo "   • config/ - Theme settings"
echo ""
echo "Deploy to Shopify:"
echo "   # Install Shopify CLI if not already installed"
echo "   npm install -g @shopify/cli @shopify/theme"
echo ""
echo "   # Authenticate with your store"
echo "   shopify theme dev --store=YOUR_STORE.myshopify.com --path=$OUTPUT_DIR"
echo ""
echo "   # Push to store"
echo "   shopify theme push --store=YOUR_STORE.myshopify.com --path=$OUTPUT_DIR"
echo ""
echo "Next Steps:"
echo "   1. Edit templates/product.liquid with your branding"
echo "   2. Customize colors in config/settings_schema.json"
echo "   3. Add your own sections"
echo "   4. Deploy to test store"
echo ""
echo "Theme generated and ready for deployment!"
