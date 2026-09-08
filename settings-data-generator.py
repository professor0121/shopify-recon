#!/usr/bin/env python3
"""
settings_data.json + settings_schema.json Generator
Reconstructs Shopify theme settings from extracted CSS values + design system.
"""
import json, re, sys
from pathlib import Path

def load_design_system(extracted_dir):
    """Load design system from various possible locations."""
    paths = [
        extracted_dir / "analysis" / "design-system.json",
        extracted_dir / "extracted" / "design-system.json",
        extracted_dir / "analysis" / "css-exact-values.json",
        extracted_dir / "extracted" / "design-tokens.json",
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}

def load_theme_css(extracted_dir):
    """Load theme.css if exists."""
    paths = [
        extracted_dir / "theme" / "assets" / "theme.css",
        extracted_dir / "analysis" / "theme.css",
    ]
    for p in paths:
        if p.exists():
            return p.read_text(encoding='utf-8', errors='replace')
    return ""

def extract_colors(design_system, css):
    """Extract color palette from design system + CSS."""
    colors = {}
    
    # From design system
    if 'colors' in design_system:
        for c in design_system['colors']:
            name = c.get('name', c.get('variable', '')).replace('--', '').replace('color_', '')
            value = c.get('value', c.get('color', ''))
            if value:
                colors[name] = value
    
    # From CSS variables
    var_matches = re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))', css)
    for name, value in var_matches:
        if any(k in name.lower() for k in ['color', 'bg', 'background', 'text', 'border', 'primary', 'secondary', 'accent']):
            colors[name] = value
    
    # Common Shopify setting names
    mapping = {
        'primary': colors.get('primary', colors.get('color_primary', '#000000')),
        'secondary': colors.get('secondary', colors.get('color_secondary', '#333333')),
        'accent': colors.get('accent', colors.get('color_accent', '#0066cc')),
        'background': colors.get('background', colors.get('bg', colors.get('color_background', '#ffffff'))),
        'text': colors.get('text', colors.get('color_text', '#333333')),
        'border': colors.get('border', colors.get('color_border', '#e0e0e0')),
    }
    
    # Try to find actual brand colors
    for name, val in colors.items():
        lower = name.lower()
        if 'brand' in lower or 'primary' in lower:
            mapping['primary'] = val
        elif 'accent' in lower or 'highlight' in lower:
            mapping['accent'] = val
    
    return mapping

def extract_typography(design_system, css):
    """Extract typography settings."""
    typo = {
        'heading_font': 'sans-serif',
        'body_font': 'sans-serif',
        'heading_size': 28,
        'body_size': 16,
        'heading_weight': 700,
        'body_weight': 400,
        'heading_case': 'none',
        'line_height': 1.5,
    }
    
    # From CSS
    font_matches = re.findall(r'--font-([\w-]+):\s*[\'"]?([^;,\"\'\n]+)', css)
    for name, value in font_matches:
        if 'heading' in name.lower() or 'head' in name.lower():
            typo['heading_font'] = value.strip().replace('_', ' ')
        elif 'body' in name.lower():
            typo['body_font'] = value.strip().replace('_', ' ')
    
    # Font sizes
    size_matches = re.findall(r'--font-size-([\w-]+):\s*(\d+(?:\.\d+)?)px', css)
    for name, size in size_matches:
        if 'heading' in name.lower() or 'h1' in name.lower():
            typo['heading_size'] = int(float(size))
        elif 'body' in name.lower() or 'base' in name.lower():
            typo['body_size'] = int(float(size))
    
    # From design system
    if 'fonts' in design_system:
        for f in design_system['fonts']:
            name = f.get('name', f.get('family', ''))
            if name:
                if 'heading' in str(f.get('role', '')).lower() or 'heading' in name.lower():
                    typo['heading_font'] = name
                else:
                    typo['body_font'] = name
    
    if 'typography' in design_system:
        t = design_system['typography']
        if 'heading_font' in t: typo['heading_font'] = t['heading_font']
        if 'body_font' in t: typo['body_font'] = t['body_font']
    
    return typo

def extract_layout(design_system, css):
    """Extract layout settings."""
    layout = {
        'container_width': 1280,
        'grid_gap': 20,
        'section_spacing': 40,
        'product_grid_columns': 4,
    }
    
    # From CSS
    width_match = re.search(r'--(?:container|max-width|page-width)[\w-]*:\s*(\d+)px', css)
    if width_match:
        layout['container_width'] = int(width_match.group(1))
    
    gap_match = re.search(r'--(?:grid-)?gap[\w-]*:\s*(\d+)px', css)
    if gap_match:
        layout['grid_gap'] = int(gap_match.group(1))
    
    # Grid columns from CSS
    col_match = re.search(r'grid-template-columns:\s*repeat\((\d+)', css)
    if col_match:
        layout['product_grid_columns'] = int(col_match.group(1))
    
    return layout

def extract_buttons(design_system, css):
    """Extract button settings."""
    buttons = {
        'button_bg': '#000000',
        'button_text': '#ffffff',
        'button_radius': 4,
        'button_padding_x': 24,
        'button_padding_y': 12,
        'button_font_size': 14,
        'button_font_weight': 600,
    }
    
    # From CSS
    radius_match = re.search(r'(?:--)?button[\w-]*radius[\w-]*:\s*(\d+)px', css)
    if radius_match:
        buttons['button_radius'] = int(radius_match.group(1))
    
    bg_match = re.search(r'(?:--)?button[\w-]*(?:bg|background)[\w-]*:\s*(#[0-9a-fA-F]{3,8})', css)
    if bg_match:
        buttons['button_bg'] = bg_match.group(1)
    
    return buttons

def generate_settings_schema(colors, typo, layout, buttons):
    """Generate settings_schema.json - Shopify format."""
    schema = [
        {
            "name": "theme_info",
            "theme_name": "Cloned Theme",
            "theme_version": "1.0.0",
            "theme_author": "Shopify Recon",
            "theme_documentation_url": "https://shopify.dev",
            "theme_support_url": "https://shopify.dev"
        },
        {
            "name": "Colors",
            "settings": [
                {"type": "color", "id": "color_primary", "label": "Primary Color", "default": colors['primary']},
                {"type": "color", "id": "color_secondary", "label": "Secondary Color", "default": colors['secondary']},
                {"type": "color", "id": "color_accent", "label": "Accent Color", "default": colors['accent']},
                {"type": "color", "id": "color_background", "label": "Background Color", "default": colors['background']},
                {"type": "color", "id": "color_text", "label": "Text Color", "default": colors['text']},
                {"type": "color", "id": "color_border", "label": "Border Color", "default": colors['border']},
            ]
        },
        {
            "name": "Typography",
            "settings": [
                {"type": "font_picker", "id": "font_heading", "label": "Heading Font", "default": f"{typo['heading_font']}_n4"},
                {"type": "font_picker", "id": "font_body", "label": "Body Font", "default": f"{typo['body_font']}_n4"},
                {"type": "range", "id": "heading_size", "label": "Heading Size", "min": 16, "max": 48, "step": 1, "unit": "px", "default": typo['heading_size']},
                {"type": "range", "id": "body_size", "label": "Body Size", "min": 12, "max": 24, "step": 1, "unit": "px", "default": typo['body_size']},
                {"type": "select", "id": "heading_weight", "label": "Heading Weight", "options": [
                    {"value": "400", "label": "Regular"},
                    {"value": "600", "label": "Semibold"},
                    {"value": "700", "label": "Bold"},
                ], "default": str(typo['heading_weight'])},
            ]
        },
        {
            "name": "Buttons",
            "settings": [
                {"type": "color", "id": "button_bg", "label": "Button Background", "default": buttons['button_bg']},
                {"type": "color", "id": "button_text", "label": "Button Text", "default": buttons['button_text']},
                {"type": "range", "id": "button_radius", "label": "Button Radius", "min": 0, "max": 30, "step": 1, "unit": "px", "default": buttons['button_radius']},
                {"type": "range", "id": "button_padding_x", "label": "Button Horizontal Padding", "min": 8, "max": 48, "step": 2, "unit": "px", "default": buttons['button_padding_x']},
                {"type": "range", "id": "button_padding_y", "label": "Button Vertical Padding", "min": 4, "max": 32, "step": 2, "unit": "px", "default": buttons['button_padding_y']},
            ]
        },
        {
            "name": "Layout",
            "settings": [
                {"type": "range", "id": "container_width", "label": "Page Width", "min": 960, "max": 1600, "step": 40, "unit": "px", "default": layout['container_width']},
                {"type": "range", "id": "grid_gap", "label": "Grid Gap", "min": 0, "max": 60, "step": 4, "unit": "px", "default": layout['grid_gap']},
                {"type": "range", "id": "section_spacing", "label": "Section Spacing", "min": 0, "max": 100, "step": 4, "unit": "px", "default": layout['section_spacing']},
                {"type": "range", "id": "product_grid_columns", "label": "Product Grid Columns (Desktop)", "min": 2, "max": 6, "step": 1, "default": layout['product_grid_columns']},
                {"type": "select", "id": "page_layout", "label": "Page Layout", "options": [
                    {"value": "full_width", "label": "Full Width"},
                    {"value": "contained", "label": "Contained"},
                ], "default": "contained"},
            ]
        },
        {
            "name": "Cart",
            "settings": [
                {"type": "select", "id": "cart_type", "label": "Cart Type", "options": [
                    {"value": "drawer", "label": "Drawer"},
                    {"value": "page", "label": "Page"},
                    {"value": "modal", "label": "Modal"},
                ], "default": "drawer"},
                {"type": "checkbox", "id": "cart_notes", "label": "Enable Cart Notes", "default": True},
                {"type": "checkbox", "id": "free_shipping_bar", "label": "Show Free Shipping Progress", "default": True},
            ]
        },
        {
            "name": "Social Media",
            "settings": [
                {"type": "text", "id": "social_facebook", "label": "Facebook URL", "default": ""},
                {"type": "text", "id": "social_twitter", "label": "Twitter URL", "default": ""},
                {"type": "text", "id": "social_instagram", "label": "Instagram URL", "default": ""},
                {"type": "text", "id": "social_youtube", "label": "YouTube URL", "default": ""},
                {"type": "text", "id": "social_tiktok", "label": "TikTok URL", "default": ""},
            ]
        },
    ]
    return schema

def generate_settings_data(colors, typo, layout, buttons):
    """Generate settings_data.json - current settings + presets."""
    current = {
        "color_primary": colors['primary'],
        "color_secondary": colors['secondary'],
        "color_accent": colors['accent'],
        "color_background": colors['background'],
        "color_text": colors['text'],
        "color_border": colors['border'],
        "font_heading": f"{typo['heading_font']}_n4",
        "font_body": f"{typo['body_font']}_n4",
        "heading_size": typo['heading_size'],
        "body_size": typo['body_size'],
        "heading_weight": str(typo['heading_weight']),
        "button_bg": buttons['button_bg'],
        "button_text": buttons['button_text'],
        "button_radius": buttons['button_radius'],
        "button_padding_x": buttons['button_padding_x'],
        "button_padding_y": buttons['button_padding_y'],
        "container_width": layout['container_width'],
        "grid_gap": layout['grid_gap'],
        "section_spacing": layout['section_spacing'],
        "product_grid_columns": layout['product_grid_columns'],
        "page_layout": "contained",
        "cart_type": "drawer",
        "cart_notes": True,
        "free_shipping_bar": True,
        "sections": {},
    }
    
    presets = {
        "Default": current.copy(),
        "Dark": {**current, "color_background": "#0a0a0a", "color_text": "#ffffff", "color_border": "#333333"},
        "Light": {**current, "color_background": "#ffffff", "color_text": "#1a1a1a"},
    }
    
    return {"current": current, "presets": presets}

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 settings-data-generator.py <extracted_dir>")
        sys.exit(1)
    
    extracted_dir = Path(sys.argv[1])
    
    print("=" * 60)
    print("Settings Data Generator")
    print(f"Input: {extracted_dir}")
    print("=" * 60)
    
    design_system = load_design_system(extracted_dir)
    css = load_theme_css(extracted_dir)
    
    print(f"Design system loaded: {bool(design_system)}")
    print(f"CSS loaded: {len(css)} chars")
    
    colors = extract_colors(design_system, css)
    typo = extract_typography(design_system, css)
    layout = extract_layout(design_system, css)
    buttons = extract_buttons(design_system, css)
    
    print(f"\nColors: {colors}")
    print(f"Typography: {typo}")
    print(f"Layout: {layout}")
    print(f"Buttons: {buttons}")
    
    schema = generate_settings_schema(colors, typo, layout, buttons)
    data = generate_settings_data(colors, typo, layout, buttons)
    
    # Output to theme config/
    config_dir = extracted_dir / "theme" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    schema_path = config_dir / "settings_schema.json"
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    data_path = config_dir / "settings_data.json"
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nGenerated:")
    print(f"   {schema_path} ({schema_path.stat().st_size:,} bytes)")
    print(f"   {data_path} ({data_path.stat().st_size:,} bytes)")
    print(f"\n   Schema groups: {len(schema)}")
    print(f"   Settings: {sum(len(s.get('settings', [])) for s in schema)}")
    print(f"   Presets: {len(data['presets'])}")

if __name__ == "__main__":
    main()
