#!/usr/bin/env python3
"""
PRODUCT SCHEMA ANALYZER - Deep Product Intelligence
Parses Shopify products.json: metafields, pricing tiers, variant matrix, JSON-LD
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 product-schema-analyzer.py <input-dir> [output-dir]
Example: python3 product-schema-analyzer.py ./allbirds-extract ./analysis
"""

import json
import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime


def load_products(input_dir):
    """Load products.json from extraction directory"""
    path = os.path.join(input_dir, "api", "products.json")
    if not os.path.exists(path):
        # Try alternate path
        path = os.path.join(input_dir, "products.json")
    with open(path) as f:
        data = json.load(f)
    return data.get("products", data) if isinstance(data, dict) else data


def load_collections(input_dir):
    """Load collections.json from extraction directory"""
    path = os.path.join(input_dir, "api", "collections.json")
    if not os.path.exists(path):
        path = os.path.join(input_dir, "collections.json")
    with open(path) as f:
        data = json.load(f)
    return data.get("collections", data) if isinstance(data, dict) else data


# ═══════════════════════════════════════════════════════════════════
# 1. METAFIELD EXTRACTOR - Parse tags like "namespace::key => value"
# ═══════════════════════════════════════════════════════════════════

def extract_metafields(products):
    """Extract structured metafields from product tags"""
    metafields = defaultdict(lambda: defaultdict(list))  # namespace::key -> value -> [product_titles]
    
    for product in products:
        tags = product.get("tags", "")
        # Tags can be string (comma-separated) or list
        if isinstance(tags, list):
            tag_list = tags
        elif isinstance(tags, str):
            tag_list = [t.strip() for t in tags.split(",")]
        else:
            continue
        for tag in tag_list:
            tag = tag.strip()
            if not tag:
                continue
            # Match pattern: namespace::key => value
            match = re.match(r'^(.+?)::(.+?)\s*=>\s*(.+)$', tag)
            if match:
                ns, key, value = match.group(1), match.group(2), match.group(3).strip()
                metafields[f"{ns}::{key}"][value].append(product["title"])
            else:
                # Regular tag
                metafields["_tags"][tag].append(product["title"])
    
    return metafields


def analyze_metafields(products):
    """Analyze metafield distribution across products"""
    metafields = extract_metafields(products)
    
    analysis = {
        "namespaces": {},
        "top_tags": [],
        "total_metafield_keys": 0,
    }
    
    for key, values in metafields.items():
        if key == "_tags":
            # Sort regular tags by frequency
            sorted_tags = sorted(values.items(), key=lambda x: len(x[1]), reverse=True)
            analysis["top_tags"] = [
                {"tag": t, "count": len(products_list), "sample_products": products_list[:3]}
                for t, products_list in sorted_tags[:20]
            ]
        else:
            ns = key.split("::")[0] if "::" in key else "other"
            if ns not in analysis["namespaces"]:
                analysis["namespaces"][ns] = {}
            
            analysis["namespaces"][ns][key] = {
                "unique_values": len(values),
                "total_products": sum(len(v) for v in values.values()),
                "values": {v: len(products_list) for v, products_list in 
                          sorted(values.items(), key=lambda x: len(x[1]), reverse=True)[:10]}
            }
            analysis["total_metafield_keys"] += 1
    
    return analysis


# ═══════════════════════════════════════════════════════════════════
# 2. PRICING TIER ANALYZER - Extract pricing strategy
# ═══════════════════════════════════════════════════════════════════

def analyze_pricing(products):
    """Analyze pricing strategy: tiers, discounts, ranges"""
    all_prices = []
    all_compare_prices = []
    discount_products = []
    free_products = []
    
    for product in products:
        for variant in product.get("variants", []):
            price = float(variant.get("price", 0))
            compare_price = float(variant.get("compare_at_price") or 0)
            
            all_prices.append(price)
            if compare_price > 0:
                all_compare_prices.append(compare_price)
            
            if compare_price > price:
                discount_products.append({
                    "title": product["title"],
                    "price": price,
                    "compare_at_price": compare_price,
                    "discount_percent": round((1 - price / compare_price) * 100, 1),
                    "discount_amount": round(compare_price - price, 2)
                })
            
            if price == 0:
                free_products.append(product["title"])
    
    # Price tier distribution
    tiers = {
        "Free ($0)": 0,
        "Under $25": 0,
        "$25-$50": 0,
        "$50-$100": 0,
        "$100-$200": 0,
        "$200-$500": 0,
        "$500+": 0
    }
    
    for price in all_prices:
        if price == 0:
            tiers["Free ($0)"] += 1
        elif price < 25:
            tiers["Under $25"] += 1
        elif price < 50:
            tiers["$25-$50"] += 1
        elif price < 100:
            tiers["$50-$100"] += 1
        elif price < 200:
            tiers["$100-$200"] += 1
        elif price < 500:
            tiers["$200-$500"] += 1
        else:
            tiers["$500+"] += 1
    
    total_priced = len(all_prices)
    
    # Sort discounts by percentage
    discount_products.sort(key=lambda x: x["discount_percent"], reverse=True)
    
    return {
        "price_stats": {
            "min": min(all_prices) if all_prices else 0,
            "max": max(all_prices) if all_prices else 0,
            "avg": round(sum(all_prices) / len(all_prices), 2) if all_prices else 0,
            "median": sorted(all_prices)[len(all_prices) // 2] if all_prices else 0,
        },
        "tier_distribution": tiers,
        "discounts": {
            "total_discounted": len(discount_products),
            "avg_discount_percent": round(
                sum(d["discount_percent"] for d in discount_products) / len(discount_products), 1
            ) if discount_products else 0,
            "max_discount_percent": discount_products[0]["discount_percent"] if discount_products else 0,
            "top_10_discounts": discount_products[:10],
        },
        "free_products": free_products,
    }


# ═══════════════════════════════════════════════════════════════════
# 3. VARIANT MATRIX BUILDER - Option combinations
# ═══════════════════════════════════════════════════════════════════

def analyze_variants(products):
    """Build variant option matrix and analyze complexity"""
    option_names = Counter()
    option_values = defaultdict(Counter)
    variant_counts = []
    multi_option_products = []
    
    for product in products:
        options = product.get("options", [])
        variants = product.get("variants", [])
        
        variant_counts.append(len(variants))
        
        for opt in options:
            name = opt.get("name", "Unknown")
            option_names[name] += 1
            for value in opt.get("values", []):
                option_values[name][value] += 1
        
        if len(options) > 1:
            multi_option_products.append({
                "title": product["title"],
                "options": [o["name"] for o in options],
                "option_count": len(options),
                "variant_count": len(variants),
            })
    
    # Find most common option names
    common_options = option_names.most_common(10)
    
    # Build option value summary (top 5 per option)
    option_summary = {}
    for name, values in option_values.items():
        option_summary[name] = {
            "unique_values": len(values),
            "top_values": values.most_common(10),
        }
    
    return {
        "option_analysis": {
            "common_option_names": [{"name": n, "product_count": c} for n, c in common_options],
            "option_details": option_summary,
        },
        "variant_stats": {
            "min_variants": min(variant_counts) if variant_counts else 0,
            "max_variants": max(variant_counts) if variant_counts else 0,
            "avg_variants": round(sum(variant_counts) / len(variant_counts), 1) if variant_counts else 0,
            "total_variants": sum(variant_counts),
        },
        "multi_option_products": multi_option_products[:20],
        "multi_option_count": len(multi_option_products),
    }


# ═══════════════════════════════════════════════════════════════════
# 4. JSON-LD / STRUCTURED DATA PARSER
# ═══════════════════════════════════════════════════════════════════

def analyze_structured_data(products):
    """Analyze structured data available in products"""
    structured = {
        "has_images": 0,
        "has_sku": 0,
        "has_weight": 0,
        "has_barcode": 0,
        "image_stats": {},
        "sku_format": [],
    }
    
    image_counts = []
    skus = []
    
    for product in products:
        images = product.get("images", [])
        if images:
            structured["has_images"] += 1
            image_counts.append(len(images))
        
        for variant in product.get("variants", []):
            if variant.get("sku"):
                structured["has_sku"] += 1
                skus.append(variant["sku"])
                # Detect SKU format
                if len(skus) <= 20:
                    sku = variant["sku"]
                    # Try to detect pattern
                    pattern = re.sub(r'[A-Z]', 'A', sku)
                    pattern = re.sub(r'[0-9]', '0', pattern)
                    if pattern not in structured["sku_format"]:
                        structured["sku_format"].append({"sku": sku, "pattern": pattern})
            
            if variant.get("grams", 0) > 0:
                structured["has_weight"] += 1
    
    structured["image_stats"] = {
        "min": min(image_counts) if image_counts else 0,
        "max": max(image_counts) if image_counts else 0,
        "avg": round(sum(image_counts) / len(image_counts), 1) if image_counts else 0,
    }
    
    return structured


# ═══════════════════════════════════════════════════════════════════
# 5. INVENTORY ANALYZER - Stock status
# ═══════════════════════════════════════════════════════════════════

def analyze_inventory(products):
    """Analyze inventory and availability"""
    total_variants = 0
    available_variants = 0
    out_of_stock = 0
    fully_out_products = []
    
    for product in products:
        variants = product.get("variants", [])
        product_available = 0
        
        for variant in variants:
            total_variants += 1
            if variant.get("available", False):
                available_variants += 1
                product_available += 1
            else:
                out_of_stock += 1
        
        if product_available == 0 and variants:
            fully_out_products.append(product["title"])
    
    return {
        "total_variants": total_variants,
        "available": available_variants,
        "out_of_stock": out_of_stock,
        "availability_rate": round(available_variants / total_variants * 100, 1) if total_variants else 0,
        "fully_out_of_stock_products": len(fully_out_products),
        "sample_out_of_stock": fully_out_products[:10],
    }


# ═══════════════════════════════════════════════════════════════════
# 6. GENERATE REPORT
# ═══════════════════════════════════════════════════════════════════

def generate_report(products, collections, output_dir):
    """Generate comprehensive analysis report"""
    
    print("PRODUCT SCHEMA ANALYZER")
    print("━" * 69)
    print(f"  Products: {len(products)}")
    print(f"  Collections: {len(collections)}")
    print()
    
    # Run all analyzers
    print("  [1/5] Extracting metafields from tags...")
    metafield_analysis = analyze_metafields(products)
    
    print("  [2/5] Analyzing pricing strategy...")
    pricing_analysis = analyze_pricing(products)
    
    print("  [3/5] Building variant matrix...")
    variant_analysis = analyze_variants(products)
    
    print("  [4/5] Parsing structured data...")
    structured_analysis = analyze_structured_data(products)
    
    print("  [5/5] Analyzing inventory...")
    inventory_analysis = analyze_inventory(products)
    
    # Save JSON output
    full_analysis = {
        "generated_at": datetime.now().isoformat(),
        "store_info": {
            "total_products": len(products),
            "total_collections": len(collections),
        },
        "metafields": metafield_analysis,
        "pricing": pricing_analysis,
        "variants": variant_analysis,
        "structured_data": structured_analysis,
        "inventory": inventory_analysis,
    }
    
    os.makedirs(output_dir, exist_ok=True)
    
    json_path = os.path.join(output_dir, "product-analysis.json")
    with open(json_path, "w") as f:
        json.dump(full_analysis, f, indent=2)
    
    # Generate markdown report
    md_path = os.path.join(output_dir, "PRODUCT-INTELLIGENCE.md")
    with open(md_path, "w") as f:
        f.write(f"""# Product Intelligence Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Store: {len(products)} products, {len(collections)} collections

---

## 1. Pricing Intelligence

### Price Statistics
| Metric | Value |
|--------|-------|
| Min Price | ${pricing_analysis['price_stats']['min']:.2f} |
| Max Price | ${pricing_analysis['price_stats']['max']:.2f} |
| Average Price | ${pricing_analysis['price_stats']['avg']:.2f} |
| Median Price | ${pricing_analysis['price_stats']['median']:.2f} |

### Price Tier Distribution
""")
        for tier, count in pricing_analysis["tier_distribution"].items():
            pct = count / len(products) * 100 if products else 0
            f.write(f"| {tier} | {count} products ({pct:.1f}%) |\n")
        
        f.write(f"""
### Discount Strategy
- **Discounted products:** {pricing_analysis['discounts']['total_discounted']}
- **Average discount:** {pricing_analysis['discounts']['avg_discount_percent']}%
- **Max discount:** {pricing_analysis['discounts']['max_discount_percent']}%

#### Top 10 Discounts
| Product | Price | Was | Discount % | Saved |
|---------|-------|-----|------------|-------|
""")
        for d in pricing_analysis["discounts"]["top_10_discounts"]:
            f.write(f"| {d['title'][:40]} | ${d['price']:.2f} | ${d['compare_at_price']:.2f} | {d['discount_percent']}% | ${d['discount_amount']:.2f} |\n")
        
        f.write(f"""
---

## 2. Variant Matrix Analysis

### Option Analysis
""")
        for opt in variant_analysis["option_analysis"]["common_option_names"]:
            f.write(f"- **{opt['name']}**: used in {opt['product_count']} products\n")
        
        f.write(f"""
### Variant Statistics
| Metric | Value |
|--------|-------|
| Min Variants per Product | {variant_analysis['variant_stats']['min_variants']} |
| Max Variants per Product | {variant_analysis['variant_stats']['max_variants']} |
| Average Variants | {variant_analysis['variant_stats']['avg_variants']} |
| Total Variants | {variant_analysis['variant_stats']['total_variants']} |

### Multi-Option Products: {variant_analysis['multi_option_count']}
""")
        for p in variant_analysis["multi_option_products"][:10]:
            f.write(f"- {p['title'][:40]} - Options: {', '.join(p['options'])} ({p['variant_count']} variants)\n")
        
        f.write(f"""
---

## 3. Metafield Intelligence

### Namespaces Found: {len(metafield_analysis['namespaces'])}
""")
        for ns, keys in metafield_analysis["namespaces"].items():
            f.write(f"\n#### Namespace: `{ns}`\n")
            for key, info in keys.items():
                f.write(f"- **{key}**: {info['unique_values']} unique values, {info['total_products']} products\n")
                for val, count in list(info["values"].items())[:5]:
                    f.write(f"  - `{val}` {count} products\n")
        
        f.write(f"""
### Top Regular Tags
""")
        for tag in metafield_analysis["top_tags"][:15]:
            f.write(f"- `{tag['tag']}` ({tag['count']} products)\n")
        
        f.write(f"""
---

## 4. Structured Data Assessment

| Data Point | Coverage |
|------------|----------|
| Has Images | {structured_analysis['has_images']}/{len(products)} ({structured_analysis['has_images']/len(products)*100:.1f}%) |
| Has SKU | {structured_analysis['has_sku']}/{len(products)} variants |
| Has Weight | {structured_analysis['has_weight']} variants |

### Image Stats
- Min images per product: {structured_analysis['image_stats']['min']}
- Max images per product: {structured_analysis['image_stats']['max']}
- Average images: {structured_analysis['image_stats']['avg']}

### SKU Format Patterns
""")
        for sku in structured_analysis["sku_format"][:10]:
            f.write(f"- `{sku['sku']}` pattern: `{sku['pattern']}`\n")
        
        f.write(f"""
---

## 5. Inventory Status

| Metric | Value |
|--------|-------|
| Total Variants | {inventory_analysis['total_variants']} |
| Available | {inventory_analysis['available']} |
| Out of Stock | {inventory_analysis['out_of_stock']} |
| Availability Rate | {inventory_analysis['availability_rate']}% |
| Fully Out of Stock Products | {inventory_analysis['fully_out_of_stock_products']} |

""")

    print()
    print("ANALYSIS COMPLETE")
    print("━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  product-analysis.json - Full structured data")
    print(f"  PRODUCT-INTELLIGENCE.md - Human-readable report")
    print()
    
    # Print summary to console
    print("KEY INSIGHTS:")
    print(f"  • Price range: ${pricing_analysis['price_stats']['min']:.2f} - ${pricing_analysis['price_stats']['max']:.2f}")
    print(f"  • Avg variants per product: {variant_analysis['variant_stats']['avg_variants']}")
    print(f"  • Discount strategy: {pricing_analysis['discounts']['total_discounted']} products on sale")
    print(f"  • Availability: {inventory_analysis['availability_rate']}% in stock")
    print(f"  • Metafield namespaces: {len(metafield_analysis['namespaces'])}")
    print(f"  • Multi-option products: {variant_analysis['multi_option_count']}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 product-schema-analyzer.py <input-dir> [output-dir]")
        print("Example: python3 product-schema-analyzer.py ./allbirds-extract ./analysis")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "analysis")
    
    products = load_products(input_dir)
    collections = load_collections(input_dir)
    
    generate_report(products, collections, output_dir)
