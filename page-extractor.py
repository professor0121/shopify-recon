#!/usr/bin/env python3
"""
PAGE-LEVEL EXTRACTOR - Scrape All Shopify Page Types
Crawls: homepage, product page, collection page, search page, cart page, 404 page
Part of Shopify Recon | 2026-06-21

Usage: python3 page-extractor.py <url> <output-dir>
Example: python3 page-extractor.py https://rothys.com ./pages
"""

import json
import sys
import os
import re
import subprocess
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse


def fetch_page(url, timeout=15):
    """Fetch a page with proper headers"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", 
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             "--max-time", str(timeout), url],
            capture_output=True, text=True
        )
        return result.stdout
    except Exception as e:
        print(f"   Error fetching {url}: {e}")
        return ""


def find_product_url(base_url, products_json_path):
    """Find a product URL from products.json"""
    if os.path.exists(products_json_path):
        with open(products_json_path) as f:
            data = json.load(f)
            products = data.get("products", data) if isinstance(data, dict) else data
            if products and len(products) > 0:
                handle = products[0].get("handle", "")
                if handle:
                    return urljoin(base_url, f"/products/{handle}")
    return None


def find_collection_url(base_url, collections_json_path):
    """Find a collection URL from collections.json"""
    if os.path.exists(collections_json_path):
        with open(collections_json_path) as f:
            data = json.load(f)
            collections = data.get("collections", data) if isinstance(data, dict) else data
            if collections and len(collections) > 0:
                handle = collections[0].get("handle", "all")
                if handle:
                    return urljoin(base_url, f"/collections/{handle}")
    return None


def extract_page_structure(html, page_type):
    """Extract structural elements from a page"""
    structure = {
        "page_type": page_type,
        "html_size": len(html),
        "sections": [],
        "forms": [],
        "scripts_inline": 0,
        "scripts_external": 0,
        "css_inline": 0,
        "css_external": 0,
        "images": 0,
        "links": 0,
    }
    
    # Detect Shopify sections
    section_ids = re.findall(r'id="(shopify-section-[^"]+)"', html)
    for sid in section_ids:
        type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+$', sid) or re.search(r'shopify-section-(\w+)$', sid)
        section_type = type_match.group(1) if type_match else "unknown"
        structure["sections"].append({"id": sid, "type": section_type})
    
    # Detect forms
    for match in re.finditer(r'<form[^>]*action="([^"]*)"[^>]*>', html, re.IGNORECASE):
        structure["forms"].append(match.group(1))
    
    # Count resources
    structure["scripts_inline"] = len(re.findall(r'<script[^>]*>(?!.*src=)', html, re.IGNORECASE))
    structure["scripts_external"] = len(re.findall(r'<script[^>]*src=', html, re.IGNORECASE))
    structure["css_inline"] = len(re.findall(r'<style', html, re.IGNORECASE))
    structure["css_external"] = len(re.findall(r'<link[^>]*rel="stylesheet"', html, re.IGNORECASE))
    structure["images"] = len(re.findall(r'<img[^>]*src=', html, re.IGNORECASE))
    structure["links"] = len(re.findall(r'<a[^>]*href=', html, re.IGNORECASE))
    
    # Page-specific extractions
    if page_type == "product":
        structure["product_data"] = extract_product_page_data(html)
    elif page_type == "collection":
        structure["collection_data"] = extract_collection_page_data(html)
    elif page_type == "search":
        structure["search_data"] = extract_search_page_data(html)
    elif page_type == "cart":
        structure["cart_data"] = extract_cart_page_data(html)
    
    return structure


def extract_product_page_data(html):
    """Extract product page specific data"""
    data = {}
    
    # Product JSON (Shopify embeds product JSON in script tags)
    product_json_match = re.search(r'<script[^>]*type="application/json"[^>]*data-product-json[^>]*>(.*?)</script>', html, re.DOTALL)
    if product_json_match:
        try:
            data["product_json"] = json.loads(product_json_match.group(1))
        except:
            data["product_json_raw"] = product_json_match.group(1)[:500]
    
    # Variant data
    variant_data = re.findall(r'variant[^}]*"id"\s*:\s*(\d+)[^}]*"price"\s*:\s*"?(\d+(?:\.\d+)?)"?', html)
    if variant_data:
        data["variants_found"] = len(variant_data)
        data["variant_ids"] = [v[0] for v in variant_data[:20]]
    
    # Product form
    form_match = re.search(r'<form[^>]*action="[^"]*cart/add[^"]*"[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    if form_match:
        form_html = form_match.group(1)
        data["has_add_to_cart_form"] = True
        data["form_fields"] = re.findall(r'<(?:input|select|textarea)[^>]*name="([^"]*)"', form_html)
    else:
        data["has_add_to_cart_form"] = False
    
    # Breadcrumbs
    breadcrumb_match = re.search(r'<nav[^>]*(?:breadcrumb|breadcrumbs)[^>]*>(.*?)</nav>', html, re.DOTALL | re.IGNORECASE)
    data["has_breadcrumbs"] = bool(breadcrumb_match)
    
    # Image gallery
    gallery_images = re.findall(r'<img[^>]*src="([^"]*)"[^>]*(?:class="[^"]*product[^"]*"|alt="[^"]*product[^"]*")', html, re.IGNORECASE)
    data["gallery_images"] = len(gallery_images)
    
    # Reviews section
    data["has_reviews"] = bool(re.search(r'reviews?|yotpo|judgeme|stamped|okendo|bazaarvoice', html, re.IGNORECASE))
    
    # Related products
    data["has_related_products"] = bool(re.search(r'related|recommend|you.may.also|similar', html, re.IGNORECASE))
    
    # Dynamic checkout button
    data["has_dynamic_checkout"] = bool(re.search(r'shopify_payment_button|dynamic-checkout|payment-button', html, re.IGNORECASE))
    
    # Size chart
    data["has_size_chart"] = bool(re.search(r'size.chart|size.guide|size-guide', html, re.IGNORECASE))
    
    return data


def extract_collection_page_data(html):
    """Extract collection page specific data"""
    data = {}
    
    # Product grid items
    product_links = re.findall(r'<a[^>]*href="[^"]*/products/([^"?]+)"', html, re.IGNORECASE)
    data["product_count_on_page"] = len(set(product_links))
    data["product_handles"] = list(set(product_links))[:30]
    
    # Filters
    data["has_filters"] = bool(re.search(r'filter|facet|refine|narrow', html, re.IGNORECASE))
    
    # Filter types detected
    filter_types = []
    if re.search(r'filter\.size|size.filter|size-filter', html, re.IGNORECASE):
        filter_types.append("size")
    if re.search(r'filter\.color|color.filter|color-filter|swatch', html, re.IGNORECASE):
        filter_types.append("color")
    if re.search(r'filter\.price|price.filter|price-range', html, re.IGNORECASE):
        filter_types.append("price")
    if re.search(r'filter\.type|product.type|product_type', html, re.IGNORECASE):
        filter_types.append("type")
    if re.search(r'filter\.vendor|brand.filter', html, re.IGNORECASE):
        filter_types.append("vendor")
    if re.search(r'filter\.tag|tag.filter', html, re.IGNORECASE):
        filter_types.append("tag")
    data["filter_types"] = filter_types
    
    # Sort dropdown
    data["has_sort"] = bool(re.search(r'sort.by|sortby|sort-by|sortBy', html, re.IGNORECASE))
    
    # Pagination
    data["has_pagination"] = bool(re.search(r'paginat|page=\d|next.page|prev.page', html, re.IGNORECASE))
    
    # Collection description
    desc_match = re.search(r'<div[^>]*class="[^"]*collection[^"]*description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    data["has_description"] = bool(desc_match)
    
    # Grid vs list layout
    data["layout"] = "grid" if re.search(r'grid|product-grid|cards', html, re.IGNORECASE) else "list" if re.search(r'list-view|product-list', html, re.IGNORECASE) else "unknown"
    
    return data


def extract_search_page_data(html):
    """Extract search page specific data"""
    data = {}
    
    # Search form
    search_form = re.search(r'<form[^>]*action="[^"]*/search[^"]*"[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    data["has_search_form"] = bool(search_form)
    
    if search_form:
        form_html = search_form.group(1)
        data["search_input_name"] = None
        input_match = re.search(r'<input[^>]*name="([^"]*)"[^>]*type="(?:search|text)"', form_html, re.IGNORECASE)
        if input_match:
            data["search_input_name"] = input_match.group(1)
        elif re.search(r'name="q"', form_html):
            data["search_input_name"] = "q"
        
        # Search filters
        data["has_type_filter"] = bool(re.search(r'type=product|type=article|type=page', form_html, re.IGNORECASE))
    
    # Search results
    product_results = re.findall(r'<a[^>]*href="[^"]*/products/([^"?]+)"', html, re.IGNORECASE)
    data["result_count"] = len(set(product_results))
    
    # Predictive search
    data["has_predictive_search"] = bool(re.search(r'predictive|autocomplete|search-suggest|live.search', html, re.IGNORECASE))
    
    # No results handling
    data["has_no_results_message"] = bool(re.search(r'no.results|nothing.found|no.matches', html, re.IGNORECASE))
    
    return data


def extract_cart_page_data(html):
    """Extract cart page specific data"""
    data = {}
    
    # Cart form
    cart_form = re.search(r'<form[^>]*action="[^"]*cart[^"]*"[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    data["has_cart_form"] = bool(cart_form)
    
    # Cart items
    data["has_cart_items"] = bool(re.search(r'cart-item|line-item|cart.product|cartProduct', html, re.IGNORECASE))
    
    # Quantity selectors
    data["has_quantity_selector"] = bool(re.search(r'quantity|qty', html, re.IGNORECASE))
    
    # Remove buttons
    data["has_remove_button"] = bool(re.search(r'remove|delete|cart.change', html, re.IGNORECASE))
    
    # Subtotal
    data["has_subtotal"] = bool(re.search(r'subtotal|total.price|cart.total', html, re.IGNORECASE))
    
    # Checkout button
    data["has_checkout_button"] = bool(re.search(r'checkout|checkout_url|/checkout', html, re.IGNORECASE))
    
    # Continue shopping link
    data["has_continue_shopping"] = bool(re.search(r'continue.shopping|keep.shopping|back.to.shop', html, re.IGNORECASE))
    
    # Empty cart message
    data["has_empty_message"] = bool(re.search(r'empty.cart|cart.empty|your.cart.is.empty', html, re.IGNORECASE))
    
    # Cart notes
    data["has_cart_note"] = bool(re.search(r'cart.note|note|special.instructions', html, re.IGNORECASE))
    
    # Shipping calculator
    data["has_shipping_calculator"] = bool(re.search(r'shipping.calculator|calculate.shipping|shipping.rates', html, re.IGNORECASE))
    
    # Discount code field
    data["has_discount_field"] = bool(re.search(r'discount|coupon|promo.code|gift.card', html, re.IGNORECASE))
    
    return data


def crawl_store(base_url, output_dir, products_json_path=None, collections_json_path=None):
    """Crawl all page types from a Shopify store"""
    
    # Ensure base URL has protocol
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    
    store_name = urlparse(base_url).netloc
    
    print(f"PAGE-LEVEL EXTRACTOR")
    print(f"━" * 69)
    print(f"  Store: {store_name}")
    print(f"  Output: {output_dir}")
    print()
    
    pages_dir = os.path.join(output_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    
    pages = {
        "homepage": {"url": base_url, "path": "/"},
        "product": {"url": None, "path": None},
        "collection": {"url": None, "path": None},
        "search": {"url": urljoin(base_url, "/search"), "path": "/search"},
        "cart": {"url": urljoin(base_url, "/cart"), "path": "/cart"},
        "404": {"url": urljoin(base_url, "/this-page-does-not-exist-404"), "path": "/404"},
    }
    
    # Find product and collection URLs
    if products_json_path:
        product_url = find_product_url(base_url, products_json_path)
        if product_url:
            pages["product"]["url"] = product_url
            pages["product"]["path"] = urlparse(product_url).path
    
    if collections_json_path:
        collection_url = find_collection_url(base_url, collections_json_path)
        if collection_url:
            pages["collection"]["url"] = collection_url
            pages["collection"]["path"] = urlparse(collection_url).path
    
    # Fetch all pages
    all_pages_data = {}
    
    for page_type, page_info in pages.items():
        url = page_info["url"]
        if not url:
            print(f"  ⏭ Skipping {page_type} (no URL available)")
            continue
        
        print(f"  Fetching {page_type}: {url}")
        html = fetch_page(url)
        
        if not html or len(html) < 500:
            print(f"      Empty or too small response ({len(html)} bytes)")
            all_pages_data[page_type] = {"url": url, "error": "empty_response", "size": len(html)}
            continue
        
        # Save raw HTML
        html_path = os.path.join(pages_dir, f"{page_type}.html")
        with open(html_path, "w") as f:
            f.write(html)
        
        # Extract structure
        structure = extract_page_structure(html, page_type)
        structure["url"] = url
        
        all_pages_data[page_type] = structure
        
        print(f"     {len(html)} bytes, {len(structure['sections'])} sections, {structure['images']} images")
        
        # Rate limit
        time.sleep(0.5)
    
    # Save combined analysis
    analysis_path = os.path.join(output_dir, "page-analysis.json")
    with open(analysis_path, "w") as f:
        json.dump({
            "store": store_name,
            "base_url": base_url,
            "analyzed_at": datetime.now().isoformat(),
            "pages": all_pages_data,
        }, f, indent=2)
    
    # Print summary
    print()
    print(f"PAGE EXTRACTION COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {pages_dir}/")
    print(f"  page-analysis.json - Combined analysis")
    print()
    print(f"PAGES EXTRACTED:")
    print(f"{'Page Type':<15} {'Size':>10} {'Sections':>10} {'Images':>10} {'Status':>10}")
    print("-" * 60)
    
    for page_type, data in all_pages_data.items():
        if "error" in data:
            print(f"{page_type:<15} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'':>10}")
        else:
            print(f"{page_type:<15} {data['html_size']:>10} {len(data['sections']):>10} {data['images']:>10} {'':>10}")
    
    # Page-specific insights
    print()
    print("PAGE INSIGHTS:")
    
    if "product" in all_pages_data and "product_data" in all_pages_data["product"]:
        pd = all_pages_data["product"]["product_data"]
        print(f"  Product Page:")
        print(f"     • Add to cart form: {'' if pd.get('has_add_to_cart_form') else ''}")
        print(f"     • Dynamic checkout: {'' if pd.get('has_dynamic_checkout') else ''}")
        print(f"     • Breadcrumbs: {'' if pd.get('has_breadcrumbs') else ''}")
        print(f"     • Reviews: {'' if pd.get('has_reviews') else ''}")
        print(f"     • Related products: {'' if pd.get('has_related_products') else ''}")
        print(f"     • Size chart: {'' if pd.get('has_size_chart') else ''}")
        print(f"     • Gallery images: {pd.get('gallery_images', 0)}")
    
    if "collection" in all_pages_data and "collection_data" in all_pages_data["collection"]:
        cd = all_pages_data["collection"]["collection_data"]
        print(f"  Collection Page:")
        print(f"     • Products on page: {cd.get('product_count_on_page', 0)}")
        print(f"     • Filters: {', '.join(cd.get('filter_types', [])) or 'none'}")
        print(f"     • Sort: {'' if cd.get('has_sort') else ''}")
        print(f"     • Pagination: {'' if cd.get('has_pagination') else ''}")
        print(f"     • Layout: {cd.get('layout', 'unknown')}")
    
    if "search" in all_pages_data and "search_data" in all_pages_data["search"]:
        sd = all_pages_data["search"]["search_data"]
        print(f"  Search Page:")
        print(f"     • Search form: {'' if sd.get('has_search_form') else ''}")
        print(f"     • Input name: {sd.get('search_input_name', 'N/A')}")
        print(f"     • Predictive: {'' if sd.get('has_predictive_search') else ''}")
        print(f"     • No results msg: {'' if sd.get('has_no_results_message') else ''}")
    
    if "cart" in all_pages_data and "cart_data" in all_pages_data["cart"]:
        cart = all_pages_data["cart"]["cart_data"]
        print(f"  Cart Page:")
        print(f"     • Cart form: {'' if cart.get('has_cart_form') else ''}")
        print(f"     • Quantity selector: {'' if cart.get('has_quantity_selector') else ''}")
        print(f"     • Remove button: {'' if cart.get('has_remove_button') else ''}")
        print(f"     • Subtotal: {'' if cart.get('has_subtotal') else ''}")
        print(f"     • Checkout button: {'' if cart.get('has_checkout_button') else ''}")
        print(f"     • Cart notes: {'' if cart.get('has_cart_note') else ''}")
        print(f"     • Discount field: {'' if cart.get('has_discount_field') else ''}")
        print(f"     • Empty cart msg: {'' if cart.get('has_empty_message') else ''}")
    
    return all_pages_data


def main():
    if len(sys.argv) < 3:
        print("PAGE-LEVEL EXTRACTOR")
        print("━" * 69)
        print()
        print("Usage: python3 page-extractor.py <url> <output-dir> [--products=PATH] [--collections=PATH]")
        print()
        print("Example:")
        print("  python3 page-extractor.py https://rothys.com ./pages")
        print("  python3 page-extractor.py https://rothys.com ./pages --products=./api/products.json")
        sys.exit(1)
    
    base_url = sys.argv[1]
    output_dir = sys.argv[2]
    
    products_path = None
    collections_path = None
    
    for arg in sys.argv[3:]:
        if arg.startswith("--products="):
            products_path = arg.split("=", 1)[1]
        elif arg.startswith("--collections="):
            collections_path = arg.split("=", 1)[1]
    
    # Try default paths
    if not products_path:
        default = os.path.join(output_dir, "api", "products.json")
        if os.path.exists(default):
            products_path = default
    if not collections_path:
        default = os.path.join(output_dir, "api", "collections.json")
        if os.path.exists(default):
            collections_path = default
    
    crawl_store(base_url, output_dir, products_path, collections_path)


if __name__ == "__main__":
    main()
