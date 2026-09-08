#!/usr/bin/env python3
"""
MULTI-STORE COMPARATOR - Competitive Intelligence Dashboard
Batch analyze multiple Shopify stores, compare side-by-side
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 multi-store-comparator.py <store1> <store2> [store3] [store4] ...
       python3 multi-store-comparator.py --file=stores.txt
Example: python3 multi-store-comparator.py allbirds.com rothys.com taylorstitch.com
"""

import json
import sys
import os
import re
import subprocess
import time
from datetime import datetime
from collections import Counter


INSPECTOR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shopify-liquid-inspector.sh")


def fetch_store_data(url, output_dir):
    """Run liquid inspector on a store and return extracted data"""
    print(f"  Extracting: {url}")
    
    # Ensure URL has protocol
    if not url.startswith("http"):
        url = "https://" + url
    
    # Run inspector
    result = subprocess.run(
        [INSPECTOR_PATH, url, output_dir],
        capture_output=True, text=True, timeout=120
    )
    
    if result.returncode != 0:
        print(f"   Inspector warning for {url}")
    
    # Load extracted data
    data = {"url": url, "timestamp": datetime.now().isoformat()}
    
    # Products
    products_path = os.path.join(output_dir, "api", "products.json")
    if os.path.exists(products_path):
        with open(products_path) as f:
            products_data = json.load(f)
            products = products_data.get("products", products_data) if isinstance(products_data, dict) else products_data
            data["products"] = products
    else:
        data["products"] = []
    
    # Collections
    collections_path = os.path.join(output_dir, "api", "collections.json")
    if os.path.exists(collections_path):
        with open(collections_path) as f:
            collections_data = json.load(f)
            collections = collections_data.get("collections", collections_data) if isinstance(collections_data, dict) else collections_data
            data["collections"] = collections
    else:
        data["collections"] = []
    
    # Theme metadata
    theme_path = os.path.join(output_dir, "theme-metadata.json")
    if os.path.exists(theme_path):
        with open(theme_path) as f:
            data["theme"] = json.load(f)
    else:
        data["theme"] = {}
    
    # Homepage HTML for section detection
    homepage_path = os.path.join(output_dir, "homepage.html")
    if os.path.exists(homepage_path):
        with open(homepage_path) as f:
            data["homepage_html"] = f.read()
    else:
        data["homepage_html"] = ""
    
    print(f"  {url}: {len(data['products'])} products, {len(data['collections'])} collections")
    return data


def compute_store_metrics(data):
    """Compute comparison metrics for a single store"""
    products = data.get("products", [])
    collections = data.get("collections", [])
    html = data.get("homepage_html", "")
    theme = data.get("theme", {})
    
    # Price metrics
    all_prices = []
    discounted_count = 0
    total_variants = 0
    available_variants = 0
    
    for product in products:
        for variant in product.get("variants", []):
            price = float(variant.get("price", 0))
            compare = float(variant.get("compare_at_price") or 0)
            all_prices.append(price)
            total_variants += 1
            
            if variant.get("available", False):
                available_variants += 1
            if compare > price:
                discounted_count += 1
    
    # Section detection from HTML
    section_ids = set(re.findall(r'data-section-id="([^"]+)"', html))
    section_types = set(re.findall(r'data-section-type="([^"]+)"', html))
    templates = set(re.findall(r'template-([a-zA-Z]+)', html))
    
    # Detect framework
    framework = "Unknown"
    if "react" in html.lower() or "__NEXT_DATA__" in html:
        framework = "React/Next.js"
    elif "vue" in html.lower():
        framework = "Vue.js"
    elif "window.Shopify" in html:
        framework = "Shopify (native)"
    
    # Product types
    product_types = Counter(p.get("product_type", "Unknown") for p in products)
    
    # Vendors
    vendors = Counter(p.get("vendor", "Unknown") for p in products)
    
    return {
        "url": data["url"],
        "theme_name": theme.get("name", "Unknown"),
        "theme_id": theme.get("id", "N/A"),
        "framework": framework,
        "total_products": len(products),
        "total_collections": len(collections),
        "total_variants": total_variants,
        "avg_variants_per_product": round(total_variants / len(products), 1) if products else 0,
        "price_min": min(all_prices) if all_prices else 0,
        "price_max": max(all_prices) if all_prices else 0,
        "price_avg": round(sum(all_prices) / len(all_prices), 2) if all_prices else 0,
        "price_median": sorted(all_prices)[len(all_prices) // 2] if all_prices else 0,
        "discounted_variants": discounted_count,
        "discount_rate": round(discounted_count / total_variants * 100, 1) if total_variants else 0,
        "availability_rate": round(available_variants / total_variants * 100, 1) if total_variants else 0,
        "section_count": len(section_ids),
        "section_types": list(section_types)[:10],
        "templates": list(templates),
        "top_product_types": product_types.most_common(5),
        "top_vendors": vendors.most_common(5),
    }


def generate_comparison_dashboard(metrics_list, output_dir):
    """Generate side-by-side comparison dashboard"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(output_dir, "comparison.json")
    with open(json_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "stores": metrics_list,
        }, f, indent=2)
    
    # Generate CSV
    csv_path = os.path.join(output_dir, "comparison.csv")
    with open(csv_path, "w") as f:
        headers = ["URL", "Theme", "Framework", "Products", "Collections", "Variants", 
                   "Avg Variants", "Price Min", "Price Max", "Price Avg", "Discount %", "Availability %",
                   "Sections", "Section Types"]
        f.write(",".join(headers) + "\n")
        for m in metrics_list:
            row = [
                m["url"], m["theme_name"], m["framework"],
                m["total_products"], m["total_collections"], m["total_variants"],
                m["avg_variants_per_product"], m["price_min"], m["price_max"], m["price_avg"],
                m["discount_rate"], m["availability_rate"],
                m["section_count"], "; ".join(m["section_types"][:5])
            ]
            f.write(",".join(str(v) for v in row) + "\n")
    
    # Generate Markdown dashboard
    md_path = os.path.join(output_dir, "COMPETITIVE-DASHBOARD.md")
    with open(md_path, "w") as f:
        f.write(f"""# Competitive Intelligence Dashboard

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Stores analyzed: {len(metrics_list)}

---

## Side-by-Side Comparison

| Metric | """ + " | ".join(m["url"].replace("https://", "").replace("http://", "") for m in metrics_list) + " |\n")
        f.write("|--------|" + "|".join(["--------"] * len(metrics_list)) + "|\n")
        
        # Row data
        rows = [
            ("Theme", "theme_name"),
            ("Framework", "framework"),
            ("Products", "total_products"),
            ("Collections", "total_collections"),
            ("Total Variants", "total_variants"),
            ("Avg Variants/Product", "avg_variants_per_product"),
            ("Min Price", "price_min"),
            ("Max Price", "price_max"),
            ("Avg Price", "price_avg"),
            ("Median Price", "price_median"),
            ("Discount Rate %", "discount_rate"),
            ("Availability %", "availability_rate"),
            ("Sections Detected", "section_count"),
        ]
        
        for label, key in rows:
            values = []
            for m in metrics_list:
                val = m[key]
                if "price" in key and isinstance(val, (int, float)):
                    values.append(f"${val:.2f}")
                else:
                    values.append(str(val))
            f.write(f"| **{label}** | " + " | ".join(values) + " |\n")
        
        # Section types per store
        f.write("\n---\n\n## Section Types Detected\n\n")
        for m in metrics_list:
            store_name = m["url"].replace("https://", "").replace("http://", "")
            f.write(f"### {store_name}\n")
            if m["section_types"]:
                for st in m["section_types"]:
                    f.write(f"- `{st}`\n")
            else:
                f.write("- (none detected)\n")
            f.write("\n")
        
        # Templates
        f.write("## Templates Detected\n\n")
        for m in metrics_list:
            store_name = m["url"].replace("https://", "").replace("http://", "")
            f.write(f"### {store_name}\n")
            if m["templates"]:
                for t in m["templates"]:
                    f.write(f"- `{t}`\n")
            else:
                f.write("- (none detected)\n")
            f.write("\n")
        
        # Product types
        f.write("## Top Product Types\n\n")
        for m in metrics_list:
            store_name = m["url"].replace("https://", "").replace("http://", "")
            f.write(f"### {store_name}\n")
            for pt, count in m["top_product_types"]:
                f.write(f"- {pt}: {count} products\n")
            f.write("\n")
        
        # Vendors
        f.write("## Top Vendors\n\n")
        for m in metrics_list:
            store_name = m["url"].replace("https://", "").replace("http://", "")
            f.write(f"### {store_name}\n")
            for v, count in m["top_vendors"]:
                f.write(f"- {v}: {count} products\n")
            f.write("\n")
        
        # Winner analysis
        f.write("## Competitive Rankings\n\n")
        
        # Most products
        f.write("### Most Products\n")
        sorted_by_products = sorted(metrics_list, key=lambda x: x["total_products"], reverse=True)
        for i, m in enumerate(sorted_by_products, 1):
            f.write(f"{i}. {m['url']} - {m['total_products']} products\n")
        
        f.write("\n### Highest Avg Price\n")
        sorted_by_price = sorted(metrics_list, key=lambda x: x["price_avg"], reverse=True)
        for i, m in enumerate(sorted_by_price, 1):
            f.write(f"{i}. {m['url']} - ${m['price_avg']:.2f}\n")
        
        f.write("\n### Most Sections (most complex theme)\n")
        sorted_by_sections = sorted(metrics_list, key=lambda x: x["section_count"], reverse=True)
        for i, m in enumerate(sorted_by_sections, 1):
            f.write(f"{i}. {m['url']} - {m['section_count']} sections\n")
        
        f.write("\n### Best Availability\n")
        sorted_by_avail = sorted(metrics_list, key=lambda x: x["availability_rate"], reverse=True)
        for i, m in enumerate(sorted_by_avail, 1):
            f.write(f"{i}. {m['url']} - {m['availability_rate']}%\n")
        
        f.write("\n### Most Aggressive Discounts\n")
        sorted_by_disc = sorted(metrics_list, key=lambda x: x["discount_rate"], reverse=True)
        for i, m in enumerate(sorted_by_disc, 1):
            f.write(f"{i}. {m['url']} - {m['discount_rate']}% discounted\n")
        
        f.write("\n---\n\n*Generated by Multi-Store Comparator v1*\n")
    
    print(f"\nDASHBOARD GENERATED")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  comparison.json - Full structured data")
    print(f"  comparison.csv - Spreadsheet-ready")
    print(f"  COMPETITIVE-DASHBOARD.md - Human-readable report")
    print()
    
    # Print summary
    print("QUICK COMPARISON:")
    print(f"{'Store':<30} {'Products':>8} {'Avg $':>8} {'Sections':>8} {'Avail %':>8}")
    print("-" * 70)
    for m in metrics_list:
        store = m["url"].replace("https://", "").replace("http://", "")[:28]
        print(f"{store:<30} {m['total_products']:>8} ${m['price_avg']:>7.2f} {m['section_count']:>8} {m['availability_rate']:>7.1f}%")


def main():
    if len(sys.argv) < 2:
        print("MULTI-STORE COMPARATOR")
        print("━" * 69)
        print()
        print("Usage:")
        print("  python3 multi-store-comparator.py <store1> <store2> [store3] ...")
        print("  python3 multi-store-comparator.py --file=stores.txt")
        print()
        print("Example:")
        print("  python3 multi-store-comparator.py allbirds.com rothys.com taylorstitch.com")
        sys.exit(1)
    
    # Parse arguments
    stores = []
    if sys.argv[1].startswith("--file="):
        file_path = sys.argv[1].split("=", 1)[1]
        with open(file_path) as f:
            stores = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        stores = sys.argv[1:]
    
    if not stores:
        print("No stores provided")
        sys.exit(1)
    
    print("MULTI-STORE COMPARATOR")
    print("━" * 69)
    print(f"  Stores to analyze: {len(stores)}")
    for s in stores:
        print(f"    • {s}")
    print()
    
    # Create output directory
    output_dir = "./_multi-store-comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch data for each store
    print("Phase 1: Extracting data from stores...\n")
    all_data = []
    for i, store_url in enumerate(stores):
        print(f"  [{i+1}/{len(stores)}] Processing {store_url}")
        store_output = os.path.join(output_dir, f"store-{i+1}")
        
        # Skip if already extracted
        products_check = os.path.join(store_output, "api", "products.json")
        if os.path.exists(products_check):
            print(f"   Using cached data for {store_url}")
            data = {"url": store_url if store_url.startswith("http") else "https://" + store_url}
            
            with open(products_check) as f:
                pdata = json.load(f)
                data["products"] = pdata.get("products", pdata) if isinstance(pdata, dict) else pdata
            
            collections_check = os.path.join(store_output, "api", "collections.json")
            if os.path.exists(collections_check):
                with open(collections_check) as f:
                    cdata = json.load(f)
                    data["collections"] = cdata.get("collections", cdata) if isinstance(cdata, dict) else cdata
            else:
                data["collections"] = []
            
            theme_check = os.path.join(store_output, "theme-metadata.json")
            if os.path.exists(theme_check):
                with open(theme_check) as f:
                    data["theme"] = json.load(f)
            else:
                data["theme"] = {}
            
            homepage_check = os.path.join(store_output, "homepage.html")
            if os.path.exists(homepage_check):
                with open(homepage_check) as f:
                    data["homepage_html"] = f.read()
            else:
                data["homepage_html"] = ""
        else:
            data = fetch_store_data(store_url, store_output)
        
        all_data.append(data)
        print()
    
    # Compute metrics
    print("Phase 2: Computing comparison metrics...\n")
    metrics_list = []
    for data in all_data:
        metrics = compute_store_metrics(data)
        metrics_list.append(metrics)
    
    # Generate dashboard
    print("Phase 3: Generating dashboard...\n")
    generate_comparison_dashboard(metrics_list, output_dir)


if __name__ == "__main__":
    main()
