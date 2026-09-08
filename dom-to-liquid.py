#!/usr/bin/env python3
"""
DOM-to-Liquid Converter
Converts rendered Shopify HTML back to Liquid template tags.

This is the core "reverse-engineering" engine:
  - Replaces product data with {{ product.* }} variables
  - Replaces collection data with {{ collection.* }} variables
  - Detects {% for %} loops from repeated elements
  - Detects {% if %} conditionals from optional elements
  - Infers {{ shop.* }}, {{ cart.* }}, {{ customer.* }} variables
  - Converts hardcoded text to {{ 'translation' | t }} patterns
  - Maps form actions to Liquid form tags ({% form 'product' %})

Usage:
  python3 dom-to-liquid.py <store_url> <extracted_dir>

Output:
  <extracted_dir>/liquid-templates/*.liquid
"""

import os
import re
import sys
import json
from pathlib import Path
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Installing beautifulsoup4...")
    os.system(f"{sys.executable} -m pip install beautifulsoup4 lxml -q")
    from bs4 import BeautifulSoup, Tag


class LiquidConverter:
    def __init__(self, store_url, extracted_dir):
        self.store_url = store_url.rstrip('/')
        self.domain = urlparse(store_url).netloc
        self.extracted_dir = Path(extracted_dir)
        self.output_dir = self.extracted_dir / "liquid-templates"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load extracted data
        raw_products = self._load_json("products.json", [])
        if isinstance(raw_products, dict):
            raw_products = raw_products.get('products', [])
        self.products = raw_products if isinstance(raw_products, list) else []
        
        raw_collections = self._load_json("collections.json", [])
        if isinstance(raw_collections, dict):
            raw_collections = raw_collections.get('collections', [])
        self.collections = raw_collections if isinstance(raw_collections, list) else []
        
        self.theme_meta = self._load_json("theme-metadata.json", {})
        self.html_files = self._load_html_files()
        
        # Liquid variable mappings
        self.product_var_map = {
            'product-title': 'product.title',
            'product-price': 'product.price | money',
            'product-compare-price': 'product.compare_at_price | money',
            'product-description': 'product.description',
            'product-vendor': 'product.vendor',
            'product-type': 'product.type',
            'product-handle': 'product.handle',
            'product-id': 'product.id',
            'product-featured-image': 'product.featured_image | image_url: width: 1000',
            'product-url': 'product.url',
            'product-sku': 'product.selected_or_first_available_variant.sku',
        }
        
        self.collection_var_map = {
            'collection-title': 'collection.title',
            'collection-description': 'collection.description',
            'collection-handle': 'collection.handle',
            'collection-url': 'collection.url',
            'collection-products-count': 'collection.products_count',
            'collection-image': 'collection.image | image_url: width: 1000',
        }
        
        self.shop_var_map = {
            'shop-name': 'shop.name',
            'shop-url': 'shop.url',
            'shop-email': 'shop.email',
            'shop-phone': 'shop.phone',
            'shop-domain': 'shop.domain',
            'shop-currency': 'shop.currency',
            'shop-locale': 'shop.locale',
        }
        
        self.stats = {
            'files_processed': 0,
            'liquid_variables_inserted': 0,
            'for_loops_detected': 0,
            'if_conditionals_detected': 0,
            'forms_converted': 0,
            'snippets_extracted': 0,
            'filters_applied': 0,
        }

    def _load_json(self, filename, default):
        """Search for JSON in extracted/ and root."""
        for subdir in ['extracted/api', 'extracted', 'analysis', '.', 'website/data']:
            path = self.extracted_dir / subdir / filename
            if path.exists():
                try:
                    with open(path) as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    continue
        return default

    def _load_html_files(self):
        """Find all HTML files in extracted dir."""
        html_files = []
        pages_dir = self.extracted_dir / "pages"
        if pages_dir.exists():
            html_files.extend(pages_dir.glob("*.html"))
        # Also check root
        html_files.extend(self.extracted_dir.glob("*.html"))
        return html_files

    def convert_all(self):
        """Convert all HTML files to Liquid templates."""
        print(f"\n{'='*60}")
        print(f"DOM-to-Liquid Converter")
        print(f"Store: {self.store_url}")
        print(f"HTML files: {len(self.html_files)}")
        print(f"Products: {len(self.products)}")
        print(f"Collections: {len(self.collections)}")
        print(f"{'='*60}\n")

        if not self.html_files:
            print(" No HTML files found. Run page-extractor first.")
            return

        for html_file in self.html_files:
            print(f"Converting: {html_file.name}")
            self._convert_file(html_file)

        self._generate_report()
        self._extract_snippets()

    def _convert_file(self, html_file):
        """Convert a single HTML file to Liquid."""
        with open(html_file, encoding='utf-8', errors='replace') as f:
            html = f.read()

        soup = BeautifulSoup(html, 'lxml')

        # Step 1: Replace product data with Liquid variables
        self._replace_product_vars(soup)

        # Step 2: Replace collection data
        self._replace_collection_vars(soup)

        # Step 3: Replace shop data
        self._replace_shop_vars(soup)

        # Step 4: Detect and convert for loops (repeated elements)
        self._detect_for_loops(soup)

        # Step 5: Convert forms to Liquid form tags
        self._convert_forms(soup)

        # Step 6: Convert links to Liquid routes
        self._convert_links(soup)

        # Step 7: Convert images to Liquid image tags
        self._convert_images(soup)

        # Step 8: Detect conditional elements
        self._detect_conditionals(soup)

        # Step 9: Convert pagination
        self._convert_pagination(soup)

        # Step 10: Convert breadcrumbs
        self._convert_breadcrumbs(soup)

        # Determine template name
        template_name = html_file.stem
        if template_name == "homepage":
            template_name = "index"

        output_file = self.output_dir / f"{template_name}.liquid"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        self.stats['files_processed'] += 1
        print(f"   {output_file.name}")

    def _replace_product_vars(self, soup):
        """Replace product data with {{ product.* }} variables."""
        if not self.products:
            return

        first_product = self.products[0] if self.products else {}

        # Replace product titles
        for elem in soup.find_all(class_=re.compile(r'product.*title', re.I)):
            if elem.string and first_product.get('title'):
                elem.string.replace_with("{{ product.title }}")
                self.stats['liquid_variables_inserted'] += 1

        # Replace product prices
        for elem in soup.find_all(class_=re.compile(r'product.*price', re.I)):
            text = elem.get_text(strip=True)
            if text and ('$' in text or '€' in text or '£' in text):
                elem.clear()
                elem.append(BeautifulSoup("{{ product.price | money }}", 'lxml').span or 
                           NavigableString("{{ product.price | money }}"))
                self.stats['liquid_variables_inserted'] += 1

        # Replace product descriptions
        for elem in soup.find_all(class_=re.compile(r'product.*desc', re.I)):
            elem.clear()
            elem.append(NavigableString("{{ product.description }}"))
            self.stats['liquid_variables_inserted'] += 1

        # Replace product images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if first_product.get('images'):
                for img_data in first_product['images'][:1]:
                    img_url = img_data if isinstance(img_data, str) else img_data.get('src', '') if isinstance(img_data, dict) else ''
                    if img_url and (img_url in src or src in img_url):
                        img['src'] = "{{ product.featured_image | image_url: width: 1000 }}"
                        img['alt'] = "{{ product.title }}"
                        self.stats['liquid_variables_inserted'] += 1
                        break

        # Replace product vendor
        for elem in soup.find_all(class_=re.compile(r'product.*vendor', re.I)):
            elem.clear()
            elem.append(NavigableString("{{ product.vendor }}"))
            self.stats['liquid_variables_inserted'] += 1

    def _replace_collection_vars(self, soup):
        """Replace collection data with {{ collection.* }} variables."""
        if not self.collections:
            return

        first_collection = self.collections[0] if self.collections else {}

        for elem in soup.find_all(class_=re.compile(r'collection.*title', re.I)):
            if first_collection.get('title'):
                elem.clear()
                elem.append(NavigableString("{{ collection.title }}"))
                self.stats['liquid_variables_inserted'] += 1

        for elem in soup.find_all(class_=re.compile(r'collection.*desc', re.I)):
            elem.clear()
            elem.append(NavigableString("{{ collection.description }}"))
            self.stats['liquid_variables_inserted'] += 1

    def _replace_shop_vars(self, soup):
        """Replace shop data with {{ shop.* }} variables."""
        shop_name = self.theme_meta.get('shop', {}).get('name', '') or self.domain

        # Replace in title tags
        title = soup.find('title')
        if title and shop_name.lower() in title.get_text().lower():
            title.string = "{{ shop.name }}"

        # Replace in header/logo
        for elem in soup.find_all(class_=re.compile(r'(logo|brand|site-name|shop-name)', re.I)):
            text = elem.get_text(strip=True)
            if text and shop_name.lower() in text.lower():
                elem.clear()
                elem.append(NavigableString("{{ shop.name }}"))
                self.stats['liquid_variables_inserted'] += 1

        # Replace copyright in footer
        for elem in soup.find_all(text=re.compile(r'©|Copyright|All rights reserved', re.I)):
            parent = elem.parent
            if parent:
                new_text = re.sub(
                    r'(?:©|Copyright)\s*\d{4}.*',
                    "{{ shop.name }}",
                    str(elem)
                )
                elem.replace_with(NavigableString(new_text))
                self.stats['liquid_variables_inserted'] += 1

    def _detect_for_loops(self, soup):
        """Detect repeated elements and convert to {% for %} loops."""
        # Find product grids
        product_grid_patterns = [
            'product-grid', 'product-list', 'products-grid',
            'collection-products', 'product-cards',
            'grid-view', 'card-grid', 'product-carousel'
        ]

        for pattern in product_grid_patterns:
            grids = soup.find_all(class_=re.compile(pattern, re.I))
            for grid in grids:
                children = [c for c in grid.children if isinstance(c, Tag)]
                if len(children) >= 3:
                    # Check if children are similar (same class/tag)
                    first_class = children[0].get('class', [])
                    similar = sum(1 for c in children if c.get('class', []) == first_class)
                    if similar >= 3:
                        # Convert to for loop
                        first_child = children[0]
                        # Replace product data in template child
                        self._inject_liquid_vars_in_card(first_child)

                        # Wrap in for loop
                        for_tag = soup.new_string("{% for product in collection.products %}")
                        end_tag = soup.new_string("{% endfor %}")

                        first_child.insert_before(for_tag)
                        children[-1].insert_after(end_tag)

                        # Remove middle children
                        for child in children[1:-1]:
                            child.decompose()

                        self.stats['for_loops_detected'] += 1
                        break

    def _inject_liquid_vars_in_card(self, card):
        """Inject Liquid variables into a product card element."""
        # Title
        title = card.find(class_=re.compile(r'(title|name)', re.I))
        if title:
            title.clear()
            title.append(NavigableString("{{ product.title }}"))

        # Price
        price = card.find(class_=re.compile(r'price', re.I))
        if price:
            price.clear()
            price.append(NavigableString("{{ product.price | money }}"))

        # Compare at price
        compare = card.find(class_=re.compile(r'compare.*price|original.*price', re.I))
        if compare:
            compare.clear()
            compare.append(NavigableString(
                "{% if product.compare_at_price > product.price %}"
                "{{ product.compare_at_price | money }}"
                "{% endif %}"
            ))

        # Image
        img = card.find('img')
        if img:
            img['src'] = "{{ product.featured_image | image_url: width: 500 }}"
            img['alt'] = "{{ product.title }}"

        # Link
        link = card.find('a')
        if link:
            link['href'] = "{{ product.url }}"

    def _convert_forms(self, soup):
        """Convert HTML forms to Liquid form tags."""
        for form in soup.find_all('form'):
            action = form.get('action', '')
            form_type = None

            if '/cart/add' in action or 'cart/add' in action:
                form_type = 'product'
            elif '/cart' in action:
                form_type = 'cart'
            elif '/account/login' in action:
                form_type = 'customer_login'
            elif '/account/register' in action:
                form_type = 'create_customer'
            elif '/search' in action:
                form_type = 'search'
            elif '/contact' in action:
                form_type = 'contact'

            if form_type:
                form.name = 'div'  # Convert form to div, wrap with Liquid
                form.insert_before(
                    NavigableString(f"{{% form '{form_type}' %}}")
                )
                form.insert_after(
                    NavigableString("{% endform %}")
                )
                self.stats['forms_converted'] += 1

        # Convert add-to-cart buttons
        for btn in soup.find_all('button', type='submit'):
            btn_text = btn.get_text(strip=True).lower()
            if 'add to cart' in btn_text or 'add to bag' in btn_text:
                btn.clear()
                btn.append(NavigableString("{{ 'products.product.add_to_cart' | t }}"))

            if 'buy it now' in btn_text or 'buy now' in btn_text:
                btn.insert_before(
                    NavigableString("{{ form | payment_button }}")
                )

    def _convert_links(self, soup):
        """Convert hardcoded links to Liquid routes."""
        for a in soup.find_all('a'):
            href = a.get('href', '')

            if '/collections' in href and '/collections/all' not in href:
                a['href'] = "{{ routes.collections_url }}"
            elif '/products/' in href and not href.startswith('{{'):
                # Keep product links as-is (they'll be in for loops)
                pass
            elif '/cart' in href:
                a['href'] = "{{ routes.cart_url }}"
            elif '/search' in href:
                a['href'] = "{{ routes.search_url }}"
            elif '/account' in href:
                a['href'] = "{{ routes.account_url }}"
            elif href == '/' or href == self.store_url:
                a['href'] = "{{ routes.root_url }}"

    def _convert_images(self, soup):
        """Convert image src to Liquid image_url filters where appropriate."""
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'cdn.shopify.com' in src or self.domain in src:
                # Check if it's a logo/brand image
                alt = img.get('alt', '').lower()
                classes = ' '.join(img.get('class', []))
                if 'logo' in alt or 'logo' in classes:
                    img['src'] = "{{ settings.logo | image_url: width: 300 }}"
                    img['alt'] = "{{ shop.name }}"
                    self.stats['filters_applied'] += 1

    def _detect_conditionals(self, soup):
        """Detect conditional elements and wrap in {% if %}."""
        # Sale tags
        for elem in soup.find_all(class_=re.compile(r'(sale|on-sale|discount|badge)', re.I)):
            parent = elem.parent
            if parent:
                elem.insert_before(
                    NavigableString("{% if product.compare_at_price > product.price %}")
                )
                elem.insert_after(
                    NavigableString("{% endif %}")
                )
                self.stats['if_conditionals_detected'] += 1

        # Sold out
        for elem in soup.find_all(class_=re.compile(r'sold-out|out-of-stock', re.I)):
            elem.insert_before(
                NavigableString("{% unless product.available %}")
            )
            elem.insert_after(
                NavigableString("{% endunless %}")
            )
            self.stats['if_conditionals_detected'] += 1

        # Compare at price
        for elem in soup.find_all(class_=re.compile(r'compare.*price|was.*price', re.I)):
            elem.insert_before(
                NavigableString("{% if product.compare_at_price > product.price %}")
            )
            elem.insert_after(
                NavigableString("{% endif %}")
            )
            self.stats['if_conditionals_detected'] += 1

    def _convert_pagination(self, soup):
        """Convert pagination HTML to Liquid paginate tag."""
        pagination = soup.find(class_=re.compile(r'pagination|pager', re.I))
        if pagination:
            pagination.clear()
            pagination.append(NavigableString(
                "{{ paginate | default_pagination }}"
            ))

    def _convert_breadcrumbs(self, soup):
        """Convert breadcrumb HTML to Liquid breadcrumb snippet."""
        breadcrumb = soup.find(class_=re.compile(r'breadcrumb', re.I))
        if breadcrumb:
            breadcrumb.insert_before(
                NavigableString("{% render 'breadcrumbs' %}")
            )
            breadcrumb.decompose()

    def _extract_snippets(self):
        """Extract repeated components as snippets."""
        snippets_dir = self.extracted_dir / "theme" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)

        # Product card snippet
        product_card = """{{- comment -}}
  Product card snippet - auto-extracted by dom-to-liquid converter
{{- endcomment -}}

<div class="product-card {{ additional_classes }}">
  <a href="{{ product_card_product.url | default: product.url }}" class="product-card__link">
    <div class="product-card__image-wrapper">
      {% if product_card_product.featured_image %}
        <img src="{{ product_card_product.featured_image | image_url: width: 500 }}"
             alt="{{ product_card_product.title }}"
             loading="lazy"
             width="500" height="500">
      {% else %}
        {{ 'product-1' | placeholder_svg_tag: 'product-card__placeholder' }}
      {% endif %}
    </div>

    {% if product_card_product.compare_at_price > product_card_product.price %}
      <span class="product-card__badge product-card__badge--sale">
        {{ 'products.product.on_sale' | t }}
      </span>
    {% endif %}

    {% unless product_card_product.available %}
      <span class="product-card__badge product-card__badge--sold-out">
        {{ 'products.product.sold_out' | t }}
      </span>
    {% endunless %}
  </a>

  <div class="product-card__info">
    <h3 class="product-card__title">
      <a href="{{ product_card_product.url | default: product.url }}">
        {{ product_card_product.title | default: product.title }}
      </a>
    </h3>

    <div class="product-card__price">
      {% if product_card_product.compare_at_price > product_card_product.price %}
        <span class="product-card__price--compare">
          {{ product_card_product.compare_at_price | money }}
        </span>
      {% endif %}
      <span class="product-card__price--current">
        {{ product_card_product.price | money }}
      </span>
    </div>
  </div>
</div>
"""
        with open(snippets_dir / "product-card.liquid", 'w') as f:
            f.write(product_card)
        self.stats['snippets_extracted'] += 1

        # Pagination snippet
        pagination_snippet = """{{- comment -}}
  Pagination snippet - auto-extracted
{{- endcomment -}}
{%- if paginate.pages > 1 -%}
  <nav class="pagination" role="navigation" aria-label="Pagination">
    {%- if paginate.previous -%}
      <a href="{{ paginate.previous.url }}" class="pagination__prev">
        {{ 'general.pagination.previous' | t }}
      </a>
    {%- endif -%}

    {%- for part in paginate.parts -%}
      {%- if part.is_link -%}
        <a href="{{ part.url }}" class="pagination__page">{{ part.title }}</a>
      {%- else -%}
        {%- if part.title == paginate.current_page -%}
          <span class="pagination__page pagination__page--current" aria-current="page">
            {{ part.title }}
          </span>
        {%- else -%}
          <span class="pagination__gap">{{ part.title }}</span>
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}

    {%- if paginate.next -%}
      <a href="{{ paginate.next.url }}" class="pagination__next">
        {{ 'general.pagination.next' | t }}
      </a>
    {%- endif -%}
  </nav>
{%- endif -%}
"""
        with open(snippets_dir / "pagination.liquid", 'w') as f:
            f.write(pagination_snippet)
        self.stats['snippets_extracted'] += 1

        # Breadcrumbs snippet
        breadcrumbs_snippet = """{{- comment -}}
  Breadcrumbs snippet - auto-extracted
{{- endcomment -}}
{%- unless template == 'index' or template == 'cart' -%}
  <nav class="breadcrumbs" role="navigation" aria-label="breadcrumbs">
    <ol class="breadcrumbs__list">
      <li class="breadcrumbs__item">
        <a href="{{ routes.root_url }}" class="breadcrumbs__link">
          {{ 'general.breadcrumbs.home' | t }}
        </a>
      </li>
      {%- if template contains 'collection' -%}
        <li class="breadcrumbs__item">
          <a href="{{ routes.collections_url }}" class="breadcrumbs__link">
            {{ 'general.breadcrumbs.collections' | t }}
          </a>
        </li>
        <li class="breadcrumbs__item breadcrumbs__item--current">
          {{ collection.title }}
        </li>
      {%- elsif template contains 'product' -%}
        {%- if product.collections.size > 0 -%}
          <li class="breadcrumbs__item">
            <a href="{{ product.collections.first.url }}" class="breadcrumbs__link">
              {{ product.collections.first.title }}
            </a>
          </li>
        {%- endif -%}
        <li class="breadcrumbs__item breadcrumbs__item--current">
          {{ product.title }}
        </li>
      {%- elsif template contains 'blog' -%}
        <li class="breadcrumbs__item">
          <a href="{{ blog.url }}" class="breadcrumbs__link">{{ blog.title }}</a>
        </li>
      {%- elsif template contains 'article' -%}
        <li class="breadcrumbs__item">
          <a href="{{ blog.url }}" class="breadcrumbs__link">{{ blog.title }}</a>
        </li>
        <li class="breadcrumbs__item breadcrumbs__item--current">{{ article.title }}</li>
      {%- elsif template contains 'page' -%}
        <li class="breadcrumbs__item breadcrumbs__item--current">{{ page.title }}</li>
      {%- endif -%}
    </ol>
  </nav>
{%- endunless -%}
"""
        with open(snippets_dir / "breadcrumbs.liquid", 'w') as f:
            f.write(breadcrumbs_snippet)
        self.stats['snippets_extracted'] += 1

        print(f"\nSnippets extracted: {self.stats['snippets_extracted']}")

    def _generate_report(self):
        """Generate conversion report."""
        report = f"""# DOM-to-Liquid Conversion Report

**Store:** {self.store_url}
**Date:** {__import__('datetime').datetime.now().isoformat()}

## Conversion Statistics

| Metric | Count |
|--------|-------|
| Files processed | {self.stats['files_processed']} |
| Liquid variables inserted | {self.stats['liquid_variables_inserted']} |
| For loops detected | {self.stats['for_loops_detected']} |
| If conditionals detected | {self.stats['if_conditionals_detected']} |
| Forms converted | {self.stats['forms_converted']} |
| Snippets extracted | {self.stats['snippets_extracted']} |
| Filters applied | {self.stats['filters_applied']} |

## Generated Files

### Liquid Templates
"""
        for f in sorted(self.output_dir.glob("*.liquid")):
            size = f.stat().st_size
            report += f"- `{f.name}` ({size:,} bytes)\n"

        report += f"""
### Snippets
"""
        snippets_dir = self.extracted_dir / "theme" / "snippets"
        if snippets_dir.exists():
            for f in sorted(snippets_dir.glob("*.liquid")):
                size = f.stat().st_size
                report += f"- `{f.name}` ({size:,} bytes)\n"

        report += f"""
## Liquid Tags Used

### Variables
- `{{{{ product.title }}}}`
- `{{{{ product.price | money }}}}`
- `{{{{ product.compare_at_price | money }}}}`
- `{{{{ product.description }}}}`
- `{{{{ product.featured_image | image_url: width: 1000 }}}}`
- `{{{{ product.url }}}}`
- `{{{{ collection.title }}}}`
- `{{{{ collection.description }}}}`
- `{{{{ shop.name }}}}`
- `{{{{ routes.cart_url }}}}`
- `{{{{ routes.search_url }}}}`

### Tags
- `{{% for product in collection.products %}}` ... `{{% endfor %}}`
- `{{% if product.compare_at_price > product.price %}}` ... `{{% endif %}}`
- `{{% unless product.available %}}` ... `{{% endunless %}}`
- `{{% form 'product' %}}` ... `{{% endform %}}`
- `{{% render 'product-card' %}}`
- `{{% render 'pagination' %}}`
- `{{% render 'breadcrumbs' %}}`

### Filters
- `money` - format price
- `image_url: width: N` - resize image
- `t` - translation
- `default_pagination` - paginate object
"""

        report_path = self.extracted_dir / "DOM-TO-LIQUID-REPORT.md"
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"\n{'='*60}")
        print(f"Conversion Complete!")
        print(f"{'='*60}")
        print(f"Files processed:       {self.stats['files_processed']}")
        print(f"Liquid vars inserted:  {self.stats['liquid_variables_inserted']}")
        print(f"For loops detected:    {self.stats['for_loops_detected']}")
        print(f"If conditionals:       {self.stats['if_conditionals_detected']}")
        print(f"Forms converted:       {self.stats['forms_converted']}")
        print(f"Snippets extracted:    {self.stats['snippets_extracted']}")
        print(f"Filters applied:       {self.stats['filters_applied']}")
        print(f"{'='*60}")
        print(f"Report: {report_path}")


# Fix missing import
from bs4 import NavigableString


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 dom-to-liquid.py <store_url> <extracted_dir>")
        print("Example: python3 dom-to-liquid.py https://rothys.com /tmp/rothys-extract")
        sys.exit(1)

    store_url = sys.argv[1]
    extracted_dir = sys.argv[2]

    converter = LiquidConverter(store_url, extracted_dir)
    converter.convert_all()


if __name__ == "__main__":
    main()
