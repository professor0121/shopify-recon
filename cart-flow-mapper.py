#!/usr/bin/env python3
"""
CART & CHECKOUT FLOW MAPPER - Trace E-commerce Flow from HTML+JS
Detects cart endpoints, checkout flow, AJAX patterns, payment integration
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 cart-flow-mapper.py <input-dir> [output-dir]
Example: python3 cart-flow-mapper.py ./rothys-extract ./flow-analysis
"""

import json
import sys
import os
import re
from collections import defaultdict
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# CART ENDPOINT DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_cart_endpoints(html):
    """Detect Shopify cart AJAX endpoints from HTML/JS"""
    endpoints = {
        "cart_add": [],
        "cart_change": [],
        "cart_update": [],
        "cart_get": [],
        "cart_clear": [],
        "checkout": [],
    }
    
    # /cart/add.js or /cart/add
    for match in re.finditer(r'["\']/cart/add(?:\.js|\.json)?["\']', html):
        endpoints["cart_add"].append({
            "url": match.group().strip("\"'"),
            "position": match.start()
        })
    
    # /cart/change.js
    for match in re.finditer(r'["\']/cart/change(?:\.js|\.json)?["\']', html):
        endpoints["cart_change"].append({
            "url": match.group().strip("\"'"),
            "position": match.start()
        })
    
    # /cart/update.js
    for match in re.finditer(r'["\']/cart/update(?:\.js|\.json)?["\']', html):
        endpoints["cart_update"].append({
            "url": match.group().strip("\"'"),
            "position": match.start()
        })
    
    # /cart.js (GET cart)
    for match in re.finditer(r'["\']/cart(?:\.js|\.json)?["\']', html):
        url = match.group().strip("\"'")
        if url in ['/cart.js', '/cart.json', '/cart']:
            endpoints["cart_get"].append({"url": url, "position": match.start()})
    
    # /cart/clear.js
    for match in re.finditer(r'["\']/cart/clear(?:\.js|\.json)?["\']', html):
        endpoints["cart_clear"].append({
            "url": match.group().strip("\"'"),
            "position": match.start()
        })
    
    # Checkout URLs
    for match in re.finditer(r'["\'](/checkout[^"\']*|/cart/checkout[^"\']*)["\']', html):
        endpoints["checkout"].append({
            "url": match.group().strip("\"'"),
            "position": match.start()
        })
    
    # Deduplicate
    for key in endpoints:
        seen = set()
        deduped = []
        for e in endpoints[key]:
            if e["url"] not in seen:
                seen.add(e["url"])
                deduped.append(e)
        endpoints[key] = deduped
    
    return endpoints


# ═══════════════════════════════════════════════════════════════════
# CART TYPE DETECTOR (drawer vs page vs modal)
# ═══════════════════════════════════════════════════════════════════

def detect_cart_type(html):
    """Detect cart implementation type"""
    cart_types = []
    
    # Drawer cart
    if re.search(r'cart-drawer|cart_drawer|mini-cart|mini_cart|slideout-cart|cart-slide', html, re.IGNORECASE):
        cart_types.append("drawer")
    
    # Page cart
    if re.search(r'class="cart-page|id="cart-page|template-cart', html, re.IGNORECASE):
        cart_types.append("page")
    
    # Modal/popup cart
    if re.search(r'cart-modal|cart_popup|cart-popup|modal.*cart|cart.*modal', html, re.IGNORECASE):
        cart_types.append("modal")
    
    # AJAX cart (inline update)
    if re.search(r'ajax.*cart|cart.*ajax|fetchCart|updateCart\(', html, re.IGNORECASE):
        cart_types.append("ajax")
    
    return cart_types if cart_types else ["unknown"]


# ═══════════════════════════════════════════════════════════════════
# PAYMENT DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_payment_methods(html):
    """Detect payment methods from HTML"""
    payments = []
    
    payment_patterns = {
        "shopify_pay": r'shopify-pay|shop_pay|shop-pay',
        "paypal": r'paypal|pay-pal',
        "apple_pay": r'apple-pay|apple_pay|ApplePay',
        "google_pay": r'google-pay|google_pay|GooglePay',
        "stripe": r'stripe',
        "klarna": r'klarna',
        "afterpay": r'afterpay|after-pay',
        "sezzle": r'sezzle',
        "affirm": r'affirm',
        "amazon_pay": r'amazon-pay|amazon_pay|AmazonPay',
    }
    
    for name, pattern in payment_patterns.items():
        if re.search(pattern, html, re.IGNORECASE):
            count = len(re.findall(pattern, html, re.IGNORECASE))
            payments.append({"method": name, "references": count})
    
    # Payment gateway divs
    gateway_divs = re.findall(r'data-payment-(?:id|type|method)="([^"]+)"', html)
    if gateway_divs:
        for gw in set(gateway_divs):
            payments.append({"method": gw, "references": gateway_divs.count(gw), "source": "gateway_div"})
    
    return payments


# ═══════════════════════════════════════════════════════════════════
# AJAX PATTERN DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_ajax_patterns(html):
    """Detect AJAX patterns used for cart operations"""
    patterns = {
        "fetch_calls": [],
        "xhr_calls": [],
        "jquery_ajax": [],
        "axios_calls": [],
    }
    
    # fetch() calls related to cart
    for match in re.finditer(r'fetch\(\s*["\']([^"\']*(?:cart|checkout|product)[^"\']*)["\']', html, re.IGNORECASE):
        patterns["fetch_calls"].append(match.group(1))
    
    # XMLHttpRequest
    for match in re.finditer(r'\.open\(\s*["\'](?:GET|POST|PUT|DELETE)["\'],?\s*["\']([^"\']*(?:cart|checkout)[^"\']*)["\']', html, re.IGNORECASE):
        patterns["xhr_calls"].append(match.group(1))
    
    # jQuery $.ajax
    for match in re.finditer(r'\$\.ajax\(\s*\{[^}]*url:\s*["\']([^"\']*(?:cart|checkout)[^"\']*)["\']', html, re.DOTALL):
        patterns["jquery_ajax"].append(match.group(1))
    
    # $.post / $.get
    for match in re.finditer(r'\$\.(?:post|get)\(\s*["\']([^"\']*(?:cart|checkout)[^"\']*)["\']', html, re.IGNORECASE):
        patterns["jquery_ajax"].append(match.group(1))
    
    # Axios
    for match in re.finditer(r'axios\.\w+\(\s*["\']([^"\']*(?:cart|checkout)[^"\']*)["\']', html, re.IGNORECASE):
        patterns["axios_calls"].append(match.group(1))
    
    # Deduplicate
    for key in patterns:
        patterns[key] = list(set(patterns[key]))[:20]
    
    return patterns


# ═══════════════════════════════════════════════════════════════════
# CHECKOUT FLOW TRACER
# ═══════════════════════════════════════════════════════════════════

def trace_checkout_flow(html):
    """Trace checkout flow steps"""
    flow = {
        "has_shopify_checkout": False,
        "has_custom_checkout": False,
        "has_express_checkout": False,
        "checkout_buttons": [],
        "form_actions": [],
    }
    
    # Shopify native checkout
    if re.search(r'/checkout|checkout_url|shopify_checkout', html, re.IGNORECASE):
        flow["has_shopify_checkout"] = True
    
    # Custom checkout
    if re.search(r'custom-checkout|custom_checkout|multi-step-checkout', html, re.IGNORECASE):
        flow["has_custom_checkout"] = True
    
    # Express checkout (Shopify Pay, Apple Pay, Google Pay)
    if re.search(r'express-checkout|express_checkout|accelerated-checkout', html, re.IGNORECASE):
        flow["has_express_checkout"] = True
    
    # Checkout buttons
    button_patterns = [
        r'<button[^>]*(?:checkout|buy-now|purchase)[^>]*>(.*?)</button>',
        r'<a[^>]*(?:checkout|buy-now|purchase)[^>]*>(.*?)</a>',
        r'class="[^"]*(?:checkout|buy-now|purchase)[^"]*"',
        r'data-checkout[^=]*="([^"]*)"',
    ]
    
    for pattern in button_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        for m in matches:
            text = m.strip()[:50] if isinstance(m, str) else str(m)[:50]
            if text:
                flow["checkout_buttons"].append(text)
    
    # Form actions
    for match in re.finditer(r'<form[^>]*action="([^"]*)"[^>]*>', html, re.IGNORECASE):
        action = match.group(1)
        if any(kw in action.lower() for kw in ['cart', 'checkout', 'add', 'product']):
            flow["form_actions"].append(action)
    
    # Deduplicate
    flow["checkout_buttons"] = list(set(flow["checkout_buttons"]))[:10]
    flow["form_actions"] = list(set(flow["form_actions"]))[:15]
    
    return flow


# ═══════════════════════════════════════════════════════════════════
# PRODUCT PAGE FLOW DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_product_flow(html):
    """Detect product page interactions"""
    flow = {
        "variant_selector": "unknown",
        "quantity_selector": False,
        "add_to_cart_form": False,
        "dynamic_checkout": False,
        "swatch_detection": False,
        "size_chart": False,
    }
    
    # Variant selector type
    if re.search(r'variant-selects|variant_selector|option-selection', html, re.IGNORECASE):
        flow["variant_selector"] = "dropdown"
    if re.search(r'variant-radio|variant.*radio|swatch|color-swatch', html, re.IGNORECASE):
        flow["variant_selector"] = "swatch"
        flow["swatch_detection"] = True
    if re.search(r'variant-button|variant.*button|size-button', html, re.IGNORECASE):
        flow["variant_selector"] = "button"
    
    # Quantity selector
    if re.search(r'quantity-selector|qty-selector|quantity.*input|qty-input', html, re.IGNORECASE):
        flow["quantity_selector"] = True
    
    # Add to cart form
    if re.search(r'action="/cart/add"|product-form|product_form', html, re.IGNORECASE):
        flow["add_to_cart_form"] = True
    
    # Dynamic checkout buttons (Buy It Now)
    if re.search(r'dynamic-checkout|shopify_payment_button|payment-button', html, re.IGNORECASE):
        flow["dynamic_checkout"] = True
    
    # Size chart
    if re.search(r'size-chart|size_chart|size-guide', html, re.IGNORECASE):
        flow["size_chart"] = True
    
    return flow


# ═══════════════════════════════════════════════════════════════════
# FLOW DIAGRAM GENERATOR (Mermaid syntax)
# ═══════════════════════════════════════════════════════════════════

def generate_mermaid_diagram(cart_endpoints, cart_type, payment_methods, checkout_flow, product_flow):
    """Generate Mermaid flow diagram"""
    
    diagram = "```mermaid\ngraph TD\n"
    
    # Product page
    diagram += "    PDP[Product Detail Page]\n"
    
    # Variant selection
    if product_flow["variant_selector"] != "unknown":
        diagram += f'    VS[Variant Selector: {product_flow["variant_selector"]}]\n'
        diagram += "    PDP --> VS\n"
    
    # Quantity
    if product_flow["quantity_selector"]:
        diagram += "    QTY[Quantity Selector]\n"
        diagram += "    PDP --> QTY\n"
    
    # Add to cart
    if product_flow["add_to_cart_form"]:
        diagram += "    ATC[Add to Cart Form]\n"
        diagram += "    PDP --> ATC\n"
    
    # Cart endpoints
    if cart_endpoints["cart_add"]:
        diagram += "    ADD[/cart/add.js/]\n"
        diagram += "    ATC -->|AJAX POST| ADD\n"
    
    # Cart type
    cart_label = " + ".join(cart_type)
    diagram += f'    CART[Cart: {cart_label}]\n'
    if cart_endpoints["cart_get"]:
        diagram += "    GET[/cart.js/]\n"
        diagram += "    CART -->|AJAX GET| GET\n"
    
    # Cart modifications
    if cart_endpoints["cart_change"]:
        diagram += "    CHG[/cart/change.js/]\n"
        diagram += "    CART -->|Update item| CHG\n"
    
    if cart_endpoints["cart_clear"]:
        diagram += "    CLR[/cart/clear.js/]\n"
        diagram += "    CART -->|Clear all| CLR\n"
    
    # Dynamic checkout (Buy Now)
    if product_flow["dynamic_checkout"]:
        diagram += "    DYN[Dynamic Checkout Button]\n"
        diagram += "    PDP -->|Skip cart| DYN\n"
    
    # Checkout
    if checkout_flow["has_express_checkout"]:
        diagram += "    EXPRESS[Express Checkout]\n"
        diagram += "    DYN --> EXPRESS\n"
    
    diagram += "    CHECKOUT[Checkout Page]\n"
    diagram += "    CART -->|Proceed to checkout| CHECKOUT\n"
    
    # Payment methods
    for pm in payment_methods[:5]:
        name = pm["method"].replace("-", "_")
        diagram += f'    PAY_{name}[{pm["method"]}]\n'
        diagram += f"    CHECKOUT --> PAY_{name}\n"
    
    diagram += "    CONFIRM[Order Confirmation]\n"
    diagram += "    CHECKOUT --> CONFIRM\n"
    
    diagram += "```\n"
    
    return diagram


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("CART & CHECKOUT FLOW MAPPER")
        print("━" * 69)
        print()
        print("Usage: python3 cart-flow-mapper.py <input-dir> [output-dir]")
        print("Example: python3 cart-flow-mapper.py ./rothys-extract ./flow")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "flow-analysis")
    
    print("CART & CHECKOUT FLOW MAPPER")
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
    
    print("  [1/6] Detecting cart endpoints...")
    cart_endpoints = detect_cart_endpoints(html)
    
    print("  [2/6] Detecting cart type...")
    cart_type = detect_cart_type(html)
    
    print("  [3/6] Detecting payment methods...")
    payments = detect_payment_methods(html)
    
    print("  [4/6] Detecting AJAX patterns...")
    ajax_patterns = detect_ajax_patterns(html)
    
    print("  [5/6] Tracing checkout flow...")
    checkout_flow = trace_checkout_flow(html)
    
    print("  [6/6] Detecting product page flow...")
    product_flow = detect_product_flow(html)
    
    # Generate Mermaid diagram
    mermaid = generate_mermaid_diagram(cart_endpoints, cart_type, payments, checkout_flow, product_flow)
    
    # Create output
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    full_analysis = {
        "generated_at": datetime.now().isoformat(),
        "source": input_dir,
        "cart_endpoints": cart_endpoints,
        "cart_type": cart_type,
        "payment_methods": payments,
        "ajax_patterns": ajax_patterns,
        "checkout_flow": checkout_flow,
        "product_flow": product_flow,
    }
    
    json_path = os.path.join(output_dir, "flow-analysis.json")
    with open(json_path, "w") as f:
        json.dump(full_analysis, f, indent=2)
    
    # Generate markdown report
    md_path = os.path.join(output_dir, "CART-FLOW-REPORT.md")
    with open(md_path, "w") as f:
        f.write(f"""# Cart & Checkout Flow Report

Source: {input_dir}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Flow Diagram

{mermaid}

---

## Cart Endpoints Detected

""")
        for name, endpoints in cart_endpoints.items():
            if endpoints:
                f.write(f"### {name.replace('_', ' ').title()}\n")
                for e in endpoints:
                    f.write(f"- `{e['url']}`\n")
                f.write("\n")
        
        f.write(f"""---

## Cart Implementation

**Type:** {', '.join(cart_type)}

---

## Payment Methods

""")
        if payments:
            f.write("| Method | References |\n|--------|------------|\n")
            for pm in payments:
                f.write(f"| {pm['method']} | {pm['references']} |\n")
        else:
            f.write("No payment methods detected on homepage.\n")
        
        f.write(f"\n---\n\n## AJAX Patterns\n\n")
        for name, calls in ajax_patterns.items():
            if calls:
                f.write(f"### {name.replace('_', ' ').title()}\n")
                for url in calls:
                    f.write(f"- `{url}`\n")
                f.write("\n")
        
        f.write(f"""---

## Checkout Flow

- **Shopify Native Checkout:** {'Yes' if checkout_flow['has_shopify_checkout'] else 'No'}
- **Custom Checkout:** {'Yes' if checkout_flow['has_custom_checkout'] else 'No'}
- **Express Checkout:** {'Yes' if checkout_flow['has_express_checkout'] else 'No'}

### Checkout Buttons Found
""")
        for btn in checkout_flow["checkout_buttons"]:
            f.write(f"- `{btn}`\n")
        
        f.write(f"\n### Form Actions\n")
        for action in checkout_flow["form_actions"]:
            f.write(f"- `{action}`\n")
        
        f.write(f"""
---

## Product Page Flow

| Feature | Status |
|---------|--------|
| Variant Selector | {product_flow['variant_selector']} |
| Quantity Selector | {'' if product_flow['quantity_selector'] else ''} |
| Add to Cart Form | {'' if product_flow['add_to_cart_form'] else ''} |
| Dynamic Checkout (Buy Now) | {'' if product_flow['dynamic_checkout'] else ''} |
| Swatch Detection | {'' if product_flow['swatch_detection'] else ''} |
| Size Chart | {'' if product_flow['size_chart'] else ''} |

---

*Generated by Cart & Checkout Flow Mapper v1*
""")
    
    # Summary
    print(f"\nFLOW MAPPING COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  flow-analysis.json - Full structured data")
    print(f"  CART-FLOW-REPORT.md - Report with Mermaid diagram")
    print()
    print("FLOW SUMMARY:")
    print(f"  • Cart type: {', '.join(cart_type)}")
    
    total_endpoints = sum(len(v) for v in cart_endpoints.values())
    print(f"  • Cart endpoints: {total_endpoints}")
    
    print(f"  • Payment methods: {len(payments)}")
    if payments:
        for pm in payments[:5]:
            print(f"    - {pm['method']} ({pm['references']} refs)")
    
    print(f"  • Variant selector: {product_flow['variant_selector']}")
    print(f"  • Dynamic checkout: {'Yes' if product_flow['dynamic_checkout'] else 'No'}")
    print(f"  • Express checkout: {'Yes' if checkout_flow['has_express_checkout'] else 'No'}")


if __name__ == "__main__":
    main()
