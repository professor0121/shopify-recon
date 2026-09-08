#!/usr/bin/env python3
"""
SHOPIFY RECON - Beautiful TUI Dashboard
Rich-powered terminal UI for store intelligence display
Part of Shopify Recon | 2026-06-21
"""

import json
import sys
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.theme import Theme

# Custom theme
recon_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green",
    "theme_name": "bold magenta",
    "price": "bold yellow",
    "label": "dim cyan",
    "value": "white",
})

console = Console(theme=recon_theme)


def render_header(store_name):
    """Render the main header banner"""
    header = Text()
    header.append("╔═══════════════════════════════════════════════════════════════╗\n", style="cyan")
    header.append("║  ", style="cyan")
    header.append("SHOPIFY RECON", style="bold cyan")
    header.append(" - Store Intelligence Report", style="white")
    # Pad to fill
    remaining = 61 - 31 - len(store_name)
    header.append(" " * max(0, 28), style="cyan")
    header.append("║\n", style="cyan")
    header.append("╠═══════════════════════════════════════════════════════════════╣\n", style="cyan")
    header.append(f"║  Store: ", style="cyan")
    header.append(store_name, style="bold white")
    header.append(" " * max(0, 61 - 11 - len(store_name)), style="cyan")
    header.append("║\n", style="cyan")
    header.append("╚═══════════════════════════════════════════════════════════════╝", style="cyan")
    console.print(header)


def render_theme_dna(dna):
    """Render Theme DNA fingerprint panel"""
    confidence = dna.get("confidence", 0)
    bar_filled = confidence // 10
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="label", width=20)
    table.add_column("value", style="value")
    
    table.add_row("Detected Theme", dna.get("detected_theme", "Unknown"))
    table.add_row("Developer", dna.get("developer", "Unknown"))
    table.add_row("Price", dna.get("price", "Unknown"))
    table.add_row("Custom Build", "Yes" if dna.get("is_custom") else "No (Theme Store)")
    table.add_row("Customization", dna.get("customization_level", "Unknown"))
    table.add_row("Confidence", f"[{bar}] {confidence}%")
    
    if dna.get("schema_name"):
        table.add_row("Schema Name", dna["schema_name"])
    if dna.get("schema_version"):
        table.add_row("Schema Version", dna["schema_version"])
    if dna.get("theme_name_raw"):
        table.add_row("Raw Theme Name", dna["theme_name_raw"])
    
    table.add_row("Sections", str(dna.get("section_count", 0)))
    
    console.print(Panel(table, title="[bold magenta]Theme DNA[/]", border_style="magenta", padding=(1, 2)))


def render_tech_stack(tech_stack):
    """Render tech stack panel"""
    tech_text = Text()
    for i, tech in enumerate(tech_stack):
        color = "cyan"
        if "Next.js" in tech:
            color = "white on black"
        elif "React" in tech:
            color = "cyan"
        elif "Vue" in tech:
            color = "green"
        elif "jQuery" in tech:
            color = "blue"
        elif "Tailwind" in tech:
            color = "cyan"
        elif "Shopify" in tech:
            color = "green"
        
        tech_text.append(f"  {tech}\n", style=color)
    
    console.print(Panel(tech_text, title="[bold cyan]Tech Stack[/]", border_style="cyan", padding=(1, 2)))


def render_store_stats(products_data, collections_data):
    """Render store statistics panel"""
    products = products_data.get("products", products_data) if isinstance(products_data, dict) else products_data
    collections = collections_data.get("collections", collections_data) if isinstance(collections_data, dict) else collections_data
    
    # Compute stats
    all_prices = []
    total_variants = 0
    available = 0
    
    for product in products:
        for variant in product.get("variants", []):
            price = float(variant.get("price", 0))
            all_prices.append(price)
            total_variants += 1
            if variant.get("available"):
                available += 1
    
    avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
    min_price = min(all_prices) if all_prices else 0
    max_price = max(all_prices) if all_prices else 0
    avail_pct = (available / total_variants * 100) if total_variants else 0
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="label", width=20)
    table.add_column("value", style="value")
    
    table.add_row("Products", str(len(products)))
    table.add_row("Collections", str(len(collections)))
    table.add_row("Total Variants", str(total_variants))
    table.add_row("Min Price", f"${min_price:.2f}")
    table.add_row("Max Price", f"${max_price:.2f}")
    table.add_row("Avg Price", f"${avg_price:.2f}")
    table.add_row("Availability", f"{avail_pct:.1f}%")
    
    console.print(Panel(table, title="[bold green]Store Statistics[/]", border_style="green", padding=(1, 2)))


def render_design_system(colors, fonts, css_vars_count):
    """Render design system panel"""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="label", width=20)
    table.add_column("value", style="value")
    
    table.add_row("Unique Colors", str(len(colors)))
    table.add_row("Font Families", str(len(fonts)))
    table.add_row("CSS Variables", str(css_vars_count))
    
    # Show top colors as swatches (text representation)
    if colors:
        color_text = Text()
        for i, (color, count) in enumerate(colors[:5]):
            color_text.append(f"  ● {color} ({count}x)\n", style="white")
        table.add_row("Top Colors", "")
    
    console.print(Panel(table, title="[bold yellow]Design System[/]", border_style="yellow", padding=(1, 2)))


def render_cart_flow(cart_data):
    """Render cart & checkout flow panel"""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="label", width=20)
    table.add_column("value", style="value")
    
    cart_types = cart_data.get("cart_type", ["unknown"])
    table.add_row("Cart Type", ", ".join(cart_types))
    
    payments = cart_data.get("payment_methods", [])
    payment_names = [p["method"] for p in payments]
    table.add_row("Payments", ", ".join(payment_names) if payment_names else "None detected")
    
    checkout = cart_data.get("checkout_flow", {})
    table.add_row("Express Checkout", "Yes" if checkout.get("has_express_checkout") else "No")
    table.add_row("Shopify Checkout", "Yes" if checkout.get("has_shopify_checkout") else "No")
    
    product_flow = cart_data.get("product_flow", {})
    table.add_row("Variant Selector", product_flow.get("variant_selector", "unknown"))
    table.add_row("Dynamic Checkout", "" if product_flow.get("dynamic_checkout") else "")
    
    console.print(Panel(table, title="[bold red]Cart & Checkout Flow[/]", border_style="red", padding=(1, 2)))


def render_apps(apps):
    """Render detected third-party apps"""
    if not apps:
        console.print(Panel("[dim]No third-party apps detected[/]", title="[bold blue]Third-Party Apps[/]", border_style="blue", padding=(1, 2)))
        return
    
    table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
    table.add_column("App", style="cyan", no_wrap=True)
    table.add_column("References", justify="right", style="yellow")
    
    for app in apps:
        table.add_row(app["app"], str(app["references"]))
    
    console.print(Panel(table, title="[bold blue]Third-Party Apps Detected[/]", border_style="blue", padding=(1, 2)))


def render_fingerprint_matches(matches):
    """Render fingerprint evidence"""
    if not matches:
        return
    
    table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
    table.add_column("Theme", style="magenta")
    table.add_column("Developer", style="cyan")
    table.add_column("Price", style="yellow")
    table.add_column("Score", justify="right", style="green")
    
    for m in matches[:5]:
        table.add_row(m["name"], m["developer"], m["price"], str(m["score"]))
    
    console.print(Panel(table, title="[bold magenta]Theme Fingerprint Matches[/]", border_style="magenta", padding=(1, 2)))


def render_footer():
    """Render footer"""
    footer = Text()
    footer.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", style="dim cyan")
    footer.append(f"Generated by Shopify Recon v3.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n", style="dim")
    footer.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim cyan")
    console.print(footer)


def render_full_report(store_name, dna, products_data, collections_data, design_colors, design_fonts, css_vars_count, cart_data, apps):
    """Render the complete TUI dashboard"""
    render_header(store_name)
    console.print()
    render_theme_dna(dna)
    console.print()
    render_tech_stack(dna.get("tech_stack", []))
    console.print()
    render_store_stats(products_data, collections_data)
    console.print()
    render_design_system(design_colors, design_fonts, css_vars_count)
    console.print()
    render_cart_flow(cart_data)
    console.print()
    render_apps(apps)
    console.print()
    render_fingerprint_matches(dna.get("fingerprint_matches", []))
    render_footer()


if __name__ == "__main__":
    # Test with Rothys data
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import theme-dna.py (hyphenated filename, need importlib)
    import importlib.util
    spec = importlib.util.spec_from_file_location("theme_dna", os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme-dna.py"))
    theme_dna_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme_dna_mod)
    ThemeDNA = theme_dna_mod.ThemeDNA
    
    html_path = "/home/ubuntu/tools/_multi-store-comparison/store-2/homepage.html"
    with open(html_path) as f:
        html = f.read()
    
    dna = ThemeDNA(html).analyze()
    
    # Load products
    with open("/home/ubuntu/tools/_multi-store-comparison/store-2/api/products.json") as f:
        products_data = json.load(f)
    with open("/home/ubuntu/tools/_multi-store-comparison/store-2/api/collections.json") as f:
        collections_data = json.load(f)
    
    # Mock design + cart data (in production, load from analysis output)
    from collections import Counter
    colors = Counter({"#03143b": 15, "#F4F2EF": 8, "#092DC5": 5, "#ffffff": 30, "#000000": 20})
    fonts = ["inherit", "Arial", "Helvetica"]
    
    cart_data = {
        "cart_type": ["drawer", "modal"],
        "payment_methods": [
            {"method": "stripe", "references": 26},
            {"method": "paypal", "references": 3},
            {"method": "apple_pay", "references": 2},
        ],
        "checkout_flow": {"has_express_checkout": True, "has_shopify_checkout": True},
        "product_flow": {"variant_selector": "button", "dynamic_checkout": False},
    }
    
    apps = [
        {"app": "swym_wishlist", "references": 418},
        {"app": "constructor_io", "references": 69},
        {"app": "fontawesome", "references": 56},
        {"app": "yotpo", "references": 2},
    ]
    
    render_full_report("rothys.com", dna, products_data, collections_data, colors.most_common(5), fonts, 226, cart_data, apps)
