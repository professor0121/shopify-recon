#!/usr/bin/env python3
"""
JS LOGIC EXTRACTOR - Extract & Map Theme JavaScript Logic
Parses inline JS, detects cart/variant/filter logic, maps to Liquid variables
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 js-logic-extractor.py <input-dir> [output-dir]
Example: python3 js-logic-extractor.py ./rothys-extract ./js-analysis
"""

import json
import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# SCRIPT EXTRACTOR - Extract all inline + external scripts
# ═══════════════════════════════════════════════════════════════════

def extract_scripts(html):
    """Extract all script tags with their content and attributes"""
    scripts = []
    
    # Inline scripts
    for match in re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.DOTALL):
        attrs_str = match.group(1)
        content = match.group(2)
        
        # Parse attributes
        attrs = {}
        for attr_match in re.finditer(r'(\w[\w-]*)=["\']([^"\']*)["\']', attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)
        
        # Skip analytics/tracking
        src = attrs.get("src", "")
        if any(x in src.lower() for x in ['google-analytics', 'gtag', 'facebook', 'fbq', 
                                            'newrelic', 'hotjar', 'segment', 'mixpanel',
                                            'connect.facebook', 'bat.bing', 'analytics']):
            continue
        
        # Skip if content is analytics
        if content and any(x in content.lower()[:500] for x in ['newrelic', 'gtag(', 'fbq(', 
                                                                 'dataLayer', 'boomerang']):
            continue
        
        scripts.append({
            "index": len(scripts),
            "attrs": attrs,
            "src": src,
            "content": content.strip(),
            "size": len(content.strip()),
            "type": "inline" if content.strip() else "external",
        })
    
    return scripts


# ═══════════════════════════════════════════════════════════════════
# FUNCTION EXTRACTOR - Parse JS function definitions
# ═══════════════════════════════════════════════════════════════════

def extract_functions(script_content):
    """Extract function definitions from JS"""
    functions = []
    
    # function name() { ... }
    for match in re.finditer(r'function\s+(\w+)\s*\([^)]*\)\s*\{', script_content):
        name = match.group(1)
        # Extract function body (approximate - find matching brace)
        start = match.end() - 1  # position of opening {
        depth = 1
        pos = match.end()
        while depth > 0 and pos < len(script_content):
            if script_content[pos] == '{':
                depth += 1
            elif script_content[pos] == '}':
                depth -= 1
            pos += 1
        body = script_content[start+1:pos-1]
        functions.append({
            "name": name,
            "body": body[:2000],  # Cap at 2KB
            "size": len(body),
        })
    
    # var name = function() { ... }
    for match in re.finditer(r'(?:var|let|const)\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{', script_content):
        name = match.group(1)
        start = match.end() - 1
        depth = 1
        pos = match.end()
        while depth > 0 and pos < len(script_content):
            if script_content[pos] == '{':
                depth += 1
            elif script_content[pos] == '}':
                depth -= 1
            pos += 1
        body = script_content[start+1:pos-1]
        functions.append({
            "name": name,
            "body": body[:2000],
            "size": len(body),
        })
    
    # object method: name: function() { ... }
    for match in re.finditer(r'(\w+)\s*:\s*function\s*\([^)]*\)\s*\{', script_content):
        name = match.group(1)
        start = match.end() - 1
        depth = 1
        pos = match.end()
        while depth > 0 and pos < len(script_content):
            if script_content[pos] == '{':
                depth += 1
            elif script_content[pos] == '}':
                depth -= 1
            pos += 1
        body = script_content[start+1:pos-1]
        functions.append({
            "name": name,
            "body": body[:2000],
            "size": len(body),
        })
    
    return functions


# ═══════════════════════════════════════════════════════════════════
# CART LOGIC DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_cart_logic(scripts):
    """Detect cart-related logic across all scripts"""
    cart_logic = {
        "add_to_cart_handlers": [],
        "cart_update_handlers": [],
        "cart_render_handlers": [],
        "cart_ajax_calls": [],
        "cart_events": [],
    }
    
    for script in scripts:
        content = script["content"]
        if not content:
            continue
        
        # Add to cart handlers
        if re.search(r'addToCart|add_to_cart|cart/add|handleAddToCart|onAddToCart', content, re.IGNORECASE):
            cart_logic["add_to_cart_handlers"].append({
                "script_index": script["index"],
                "pattern": "add_to_cart",
            })
        
        # Cart update
        if re.search(r'updateCart|update_cart|cart/change|cart/update|handleCartUpdate', content, re.IGNORECASE):
            cart_logic["cart_update_handlers"].append({
                "script_index": script["index"],
                "pattern": "update_cart",
            })
        
        # Cart render
        if re.search(r'renderCart|cartTemplate|displayCart|showCart|openCart|cartDrawer', content, re.IGNORECASE):
            cart_logic["cart_render_handlers"].append({
                "script_index": script["index"],
                "pattern": "render_cart",
            })
        
        # AJAX calls to cart
        ajax_urls = re.findall(r'(?:fetch|XMLHttpRequest|\.ajax|\.post|\.get)\s*\(\s*["\']([^"\']*(?:cart|checkout)[^"\']*)["\']', content, re.IGNORECASE)
        for url in ajax_urls:
            cart_logic["cart_ajax_calls"].append({
                "script_index": script["index"],
                "url": url,
            })
        
        # Cart event listeners
        cart_events = re.findall(r'addEventListener\(\s*["\'](\w+)["\']\s*,\s*\w*(?:cart|Cart)\w*', content)
        for evt in cart_events:
            cart_logic["cart_events"].append({
                "script_index": script["index"],
                "event": evt,
            })
    
    return cart_logic


# ═══════════════════════════════════════════════════════════════════
# VARIANT LOGIC DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_variant_logic(scripts):
    """Detect variant selection logic"""
    variant_logic = {
        "select_callback": None,
        "variant_handlers": [],
        "variant_events": [],
        "option_selectors": [],
    }
    
    for script in scripts:
        content = script["content"]
        if not content:
            continue
        
        # selectCallback (Shopify standard)
        if re.search(r'selectCallback|select_callback', content, re.IGNORECASE):
            # Extract the function body
            match = re.search(r'(?:window\.)?selectCallback\s*=\s*function\s*\(([^)]*)\)\s*\{', content)
            if match:
                params = match.group(1)
                start = match.end() - 1
                depth = 1
                pos = match.end()
                while depth > 0 and pos < len(content):
                    if content[pos] == '{':
                        depth += 1
                    elif content[pos] == '}':
                        depth -= 1
                    pos += 1
                body = content[start+1:pos-1]
                variant_logic["select_callback"] = {
                    "params": params,
                    "body": body[:3000],
                    "script_index": script["index"],
                }
        
        # Variant change handlers
        if re.search(r'variant.*change|change.*variant|onVariantChange|variantChange', content, re.IGNORECASE):
            variant_logic["variant_handlers"].append({
                "script_index": script["index"],
                "pattern": "variant_change",
            })
        
        # Option selectors
        if re.search(r'option-selection|option_selection|OptionSelect|variant-selects', content, re.IGNORECASE):
            variant_logic["option_selectors"].append({
                "script_index": script["index"],
                "pattern": "option_selector",
            })
        
        # Swym variant events (wishlist integration)
        if re.search(r'triggerSwymVariantEvent|SwymProductVariants', content):
            variant_logic["variant_handlers"].append({
                "script_index": script["index"],
                "pattern": "swym_variant",
            })
    
    return variant_logic


# ═══════════════════════════════════════════════════════════════════
# SHOPIFY DATA MAPPER - Map JS variables to Shopify objects
# ═══════════════════════════════════════════════════════════════════

def map_shopify_data(scripts):
    """Map JavaScript references to Shopify Liquid objects"""
    mappings = {
        "product": [],
        "cart": [],
        "shop": [],
        "collection": [],
        "customer": [],
        "variant": [],
    }
    
    for script in scripts:
        content = script["content"]
        if not content:
            continue
        
        # Shopify.product references
        for match in re.finditer(r'(?:window\.)?Shopify\.product\.(\w+)', content):
            mappings["product"].append({
                "property": match.group(1),
                "script_index": script["index"],
            })
        
        # Shopify.cart references
        for match in re.finditer(r'(?:window\.)?Shopify\.cart\.(\w+)', content):
            mappings["cart"].append({
                "property": match.group(1),
                "script_index": script["index"],
            })
        
        # Shopify.shop references
        for match in re.finditer(r'(?:window\.)?Shopify\.shop\.(\w+)', content):
            mappings["shop"].append({
                "property": match.group(1),
                "script_index": script["index"],
            })
        
        # Shopify.customer references
        for match in re.finditer(r'(?:window\.)?Shopify\.customer\.(\w+)', content):
            mappings["customer"].append({
                "property": match.group(1),
                "script_index": script["index"],
            })
        
        # Liquid-style product variables in JS (e.g., {{ product.id }} rendered as numbers)
        product_vars = re.findall(r'(?:var\s+)?(?:product|Product)\.(\w+)\s*=', content)
        for var in product_vars:
            mappings["product"].append({
                "property": var,
                "script_index": script["index"],
                "source": "js_var",
            })
        
        # Cart variables
        cart_vars = re.findall(r'(?:var\s+)?(?:cart|Cart)\.(\w+)\s*=', content)
        for var in cart_vars:
            mappings["cart"].append({
                "property": var,
                "script_index": script["index"],
                "source": "js_var",
            })
    
    # Deduplicate
    for key in mappings:
        seen = set()
        deduped = []
        for m in mappings[key]:
            sig = f"{m['property']}_{m.get('source', 'shopify')}"
            if sig not in seen:
                seen.add(sig)
                deduped.append(m)
        mappings[key] = deduped
    
    return mappings


# ═══════════════════════════════════════════════════════════════════
# THIRD-PARTY APP DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_third_party_apps(scripts):
    """Detect third-party Shopify apps from script references"""
    apps = []
    
    app_patterns = {
        "swym_wishlist": r'swym|SwymProductVariants|triggerSwymVariantEvent',
        "klaviyo": r'klaviyo|kl_id|__klKey',
        "yotpo": r'yotpo|yotpoApi',
        "judge_me": r'judgeme|jdgm',
        "stamped": r'stamped|StampedFn',
        "recharge": r'recharge|ReCharge',
        "gorgias": r'gorgias',
        "tidio": r'tidio',
        "loyalty_lion": r'loyaltylion|loyalty_lion',
        "searchanise": r'searchanise',
        "algolia": r'algolia',
        "klevu": r'klevu',
        "constructor_io": r'cnstrc|constructor',
        "bazaarvoice": r'bazaarvoice|BVRR',
        "okendo": r'okendo',
        "fontawesome": r'fontawesome|fa-',
        "optimizely": r'optimizely',
        "sentry": r'sentry',
    }
    
    all_content = " ".join([s["content"] for s in scripts if s["content"]])
    
    for app_name, pattern in app_patterns.items():
        matches = re.findall(pattern, all_content, re.IGNORECASE)
        if matches:
            apps.append({
                "app": app_name,
                "references": len(matches),
            })
    
    return apps


# ═══════════════════════════════════════════════════════════════════
# LIQUID MAPPING GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_liquid_mappings(shopify_data, cart_logic, variant_logic):
    """Generate Liquid variable mappings for theme development"""
    mappings = []
    
    # Product mappings
    for m in shopify_data["product"]:
        liquid_var = f"product.{m['property']}"
        js_var = f"Shopify.product.{m['property']}"
        mappings.append({
            "liquid": liquid_var,
            "javascript": js_var,
            "type": "product",
            "usage": f"Access product {m['property']} in JS",
        })
    
    # Cart mappings
    for m in shopify_data["cart"]:
        liquid_var = f"cart.{m['property']}"
        js_var = f"Shopify.cart.{m['property']}"
        mappings.append({
            "liquid": liquid_var,
            "javascript": js_var,
            "type": "cart",
            "usage": f"Access cart {m['property']} in JS",
        })
    
    # Cart AJAX endpoints
    for call in cart_logic["cart_ajax_calls"]:
        mappings.append({
            "liquid": "form action",
            "javascript": f'fetch("{call["url"]}")',
            "type": "ajax_endpoint",
            "usage": f"Cart AJAX call to {call['url']}",
        })
    
    # Variant callback
    if variant_logic["select_callback"]:
        mappings.append({
            "liquid": "variant.id, variant.price, variant.available",
            "javascript": "selectCallback(variant)",
            "type": "variant_callback",
            "usage": "Shopify variant selection callback - fires on option change",
        })
    
    return mappings


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("JS LOGIC EXTRACTOR")
        print("━" * 69)
        print()
        print("Usage: python3 js-logic-extractor.py <input-dir> [output-dir]")
        print("Example: python3 js-logic-extractor.py ./rothys-extract ./js")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "js-analysis")
    
    print("JS LOGIC EXTRACTOR")
    print("━" * 69)
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print()
    
    # Load HTML
    html_path = os.path.join(input_dir, "homepage.html")
    if not os.path.exists(html_path):
        print(f"No homepage.html found in {input_dir}")
        sys.exit(1)
    
    with open(html_path) as f:
        html = f.read()
    
    print(f"  HTML loaded: {len(html)} bytes")
    
    print("  [1/6] Extracting scripts...")
    scripts = extract_scripts(html)
    inline_scripts = [s for s in scripts if s["type"] == "inline" and s["size"] > 100]
    print(f"    {len(scripts)} total scripts, {len(inline_scripts)} inline (non-trivial)")
    
    print("  [2/6] Extracting functions...")
    all_functions = []
    for script in inline_scripts:
        funcs = extract_functions(script["content"])
        for f in funcs:
            f["script_index"] = script["index"]
        all_functions.extend(funcs)
    print(f"    {len(all_functions)} functions found")
    
    print("  [3/6] Detecting cart logic...")
    cart_logic = detect_cart_logic(scripts)
    
    print("  [4/6] Detecting variant logic...")
    variant_logic = detect_variant_logic(scripts)
    
    print("  [5/6] Mapping Shopify data...")
    shopify_data = map_shopify_data(scripts)
    
    print("  [6/6] Detecting third-party apps...")
    third_party = detect_third_party_apps(scripts)
    
    # Generate Liquid mappings
    liquid_mappings = generate_liquid_mappings(shopify_data, cart_logic, variant_logic)
    
    # Build full analysis
    full_analysis = {
        "generated_at": datetime.now().isoformat(),
        "source": input_dir,
        "stats": {
            "total_scripts": len(scripts),
            "inline_scripts": len(inline_scripts),
            "functions_found": len(all_functions),
            "third_party_apps": len(third_party),
            "liquid_mappings": len(liquid_mappings),
        },
        "scripts": [
            {
                "index": s["index"],
                "type": s["type"],
                "src": s["src"][:200] if s["src"] else None,
                "size": s["size"],
            } for s in scripts if s["size"] > 50
        ],
        "functions": [
            {
                "name": f["name"],
                "size": f["size"],
                "script_index": f["script_index"],
                "body_preview": f["body"][:200],
            } for f in all_functions
        ],
        "cart_logic": cart_logic,
        "variant_logic": {
            "has_select_callback": variant_logic["select_callback"] is not None,
            "select_callback": variant_logic["select_callback"],
            "variant_handlers": variant_logic["variant_handlers"],
            "option_selectors": variant_logic["option_selectors"],
        },
        "shopify_data_mapping": shopify_data,
        "third_party_apps": third_party,
        "liquid_mappings": liquid_mappings,
    }
    
    # Create output
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(output_dir, "js-analysis.json")
    with open(json_path, "w") as f:
        json.dump(full_analysis, f, indent=2, default=str)
    
    # Save selectCallback body if found
    if variant_logic["select_callback"]:
        callback_path = os.path.join(output_dir, "selectCallback.js")
        with open(callback_path, "w") as f:
            f.write(f"// selectCallback - Shopify variant selection handler\n")
            f.write(f"// Extracted from {input_dir}\n\n")
            f.write(f"window.selectCallback = function({variant_logic['select_callback']['params']}) {{\n")
            f.write(variant_logic["select_callback"]["body"])
            f.write("\n};\n")
    
    # Generate markdown report
    md_path = os.path.join(output_dir, "JS-LOGIC-REPORT.md")
    with open(md_path, "w") as f:
        f.write(f"""# JS Logic Extraction Report

Source: {input_dir}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts | {len(scripts)} |
| Inline Scripts (>100b) | {len(inline_scripts)} |
| Functions Extracted | {len(all_functions)} |
| Third-Party Apps | {len(third_party)} |
| Liquid Mappings | {len(liquid_mappings)} |

---

## Functions Found

""")
        for func in all_functions:
            f.write(f"### `{func['name']}()` ({func['size']} bytes)\n")
            f.write(f"Script index: {func['script_index']}\n")
            f.write(f"```javascript\n{func['body'][:500]}\n```\n\n")
        
        f.write("## Cart Logic\n\n")
        f.write(f"- Add to cart handlers: {len(cart_logic['add_to_cart_handlers'])}\n")
        f.write(f"- Cart update handlers: {len(cart_logic['cart_update_handlers'])}\n")
        f.write(f"- Cart render handlers: {len(cart_logic['cart_render_handlers'])}\n")
        f.write(f"- Cart AJAX calls: {len(cart_logic['cart_ajax_calls'])}\n")
        
        if cart_logic["cart_ajax_calls"]:
            f.write("\n### AJAX Endpoints\n\n")
            for call in cart_logic["cart_ajax_calls"]:
                f.write(f"- `fetch('{call['url']}')` - Script #{call['script_index']}\n")
        
        f.write(f"\n---\n\n## Variant Logic\n\n")
        f.write(f"- **selectCallback:** {'Found' if variant_logic['select_callback'] else 'Not found'}\n")
        f.write(f"- Variant handlers: {len(variant_logic['variant_handlers'])}\n")
        f.write(f"- Option selectors: {len(variant_logic['option_selectors'])}\n")
        
        if variant_logic["select_callback"]:
            f.write(f"\n### selectCallback Body\n\n```javascript\n")
            f.write(f"window.selectCallback = function({variant_logic['select_callback']['params']}) {{\n")
            f.write(variant_logic["select_callback"]["body"][:1000])
            f.write("\n};\n```\n")
        
        f.write(f"\n---\n\n## Shopify Data Mapping\n\n")
        f.write("| Liquid Variable | JavaScript Equivalent | Type |\n|-----------------|----------------------|------|\n")
        for m in liquid_mappings:
            f.write(f"| `{m['liquid']}` | `{m['javascript']}` | {m['type']} |\n")
        
        f.write(f"\n---\n\n## Third-Party Apps\n\n")
        if third_party:
            f.write("| App | References |\n|-----|------------|\n")
            for app in third_party:
                f.write(f"| {app['app']} | {app['references']} |\n")
        else:
            f.write("No third-party apps detected.\n")
        
        f.write(f"\n---\n\n## Generated Files\n\n")
        f.write(f"- `js-analysis.json` - Full structured analysis\n")
        if variant_logic["select_callback"]:
            f.write(f"- `selectCallback.js` - Extracted variant callback\n")
        f.write(f"- `JS-LOGIC-REPORT.md` - This report\n")
    
    # Summary
    print(f"\nJS LOGIC EXTRACTION COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  js-analysis.json - Full structured data")
    print(f"  JS-LOGIC-REPORT.md - Analysis report")
    if variant_logic["select_callback"]:
        print(f"  selectCallback.js - Variant callback extracted")
    print()
    print("JS LOGIC SUMMARY:")
    print(f"  • Functions found: {len(all_functions)}")
    print(f"  • Cart AJAX calls: {len(cart_logic['cart_ajax_calls'])}")
    print(f"  • selectCallback: {'Found ' if variant_logic['select_callback'] else 'Not found '}")
    print(f"  • Third-party apps: {len(third_party)}")
    for app in third_party[:5]:
        print(f"    - {app['app']} ({app['references']} refs)")
    print(f"  • Liquid mappings: {len(liquid_mappings)}")


if __name__ == "__main__":
    main()
