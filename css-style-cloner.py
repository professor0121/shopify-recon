#!/usr/bin/env python3
"""
CSS/STYLE CLONER - Extract Design System from Shopify Store
Parses HTML + inline styles, extracts colors/fonts/spacing, generates theme.css + settings_schema
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 css-style-cloner.py <input-dir> [output-dir]
Example: python3 css-style-cloner.py ./rothys-extract ./cloned-styles
"""

import json
import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# COLOR EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_colors(html):
    """Extract all colors from HTML inline styles and style tags"""
    colors = Counter()
    
    # Hex colors (#fff, #ffffff, #ffffffff)
    hex_matches = re.findall(r'#([0-9a-fA-F]{3,8})\b', html)
    for hex_color in hex_matches:
        # Normalize to 6-digit
        if len(hex_color) == 3:
            normalized = ''.join(c * 2 for c in hex_color)
        elif len(hex_color) >= 6:
            normalized = hex_color[:6]
        else:
            continue
        colors[f"#{normalized.lower()}"] += 1
    
    # RGB/RGBA colors
    rgb_matches = re.findall(r'rgba?\([^)]+\)', html)
    for rgb in rgb_matches:
        colors[rgb.strip()] += 1
    
    # Named colors in CSS
    named_colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'gray', 'grey',
                    'transparent', 'inherit', 'initial', 'navy', 'purple', 'pink', 'orange',
                    'brown', 'cyan', 'magenta', 'teal', 'lime', 'maroon', 'olive', 'silver']
    for named in named_colors:
        count = len(re.findall(rf'\b{named}\b', html, re.IGNORECASE))
        if count > 0:
            colors[named.lower()] += count
    
    return colors


def categorize_colors(colors):
    """Categorize colors by likely usage (background, text, accent)"""
    # Sort by frequency
    sorted_colors = colors.most_common(30)
    
    categories = {
        "backgrounds": [],
        "text": [],
        "accents": [],
        "borders": [],
        "all": [],
    }
    
    # Heuristics
    for color, count in sorted_colors:
        color_lower = color.lower()
        
        # Skip transparent/inherit
        if color_lower in ['transparent', 'inherit', 'initial', 'rgba(0,0,0,0)']:
            continue
        
        # White and very light = likely background
        if color_lower in ['#fff', '#ffffff', 'white'] or (color_lower.startswith('#') and 
            all(int(c, 16) > 230 for c in [color_lower[1:3], color_lower[3:5], color_lower[5:7]] if len(color_lower) == 7)):
            categories["backgrounds"].append({"color": color, "count": count})
        
        # Black and very dark = likely text
        elif color_lower in ['#000', '#000000', 'black'] or (color_lower.startswith('#') and
            all(int(c, 16) < 30 for c in [color_lower[1:3], color_lower[3:5], color_lower[5:7]] if len(color_lower) == 7)):
            categories["text"].append({"color": color, "count": count})
        
        # Gray tones = likely borders or secondary text
        elif color_lower.startswith('#') and len(color_lower) == 7:
            r, g, b = int(color_lower[1:3], 16), int(color_lower[3:5], 16), int(color_lower[5:7], 16)
            if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
                # It's a gray
                if r < 100:
                    categories["text"].append({"color": color, "count": count})
                else:
                    categories["borders"].append({"color": color, "count": count})
            else:
                # Has color = accent
                categories["accents"].append({"color": color, "count": count})
        else:
            categories["all"].append({"color": color, "count": count})
        
        categories["all"].append({"color": color, "count": count})
    
    # Deduplicate "all"
    seen = set()
    deduped = []
    for c in categories["all"]:
        if c["color"] not in seen:
            seen.add(c["color"])
            deduped.append(c)
    categories["all"] = deduped[:20]
    
    return categories


# ═══════════════════════════════════════════════════════════════════
# FONT EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_fonts(html):
    """Extract font families and sizes from HTML"""
    fonts = Counter()
    font_sizes = Counter()
    font_weights = Counter()
    
    # Font families
    font_family_matches = re.findall(r'font-family:\s*([^;"}]+)', html)
    for ff in font_family_matches:
        # Clean up
        ff = ff.strip().rstrip(',').strip("'\"")
        # Take first font in stack
        primary = ff.split(',')[0].strip().strip("'\"")
        fonts[primary] += 1
    
    # Font sizes
    size_matches = re.findall(r'font-size:\s*(\d+(?:\.\d+)?(?:px|rem|em|pt|%)?)', html)
    for size in size_matches:
        font_sizes[size] += 1
    
    # Font weights
    weight_matches = re.findall(r'font-weight:\s*(\w+|\d+)', html)
    for weight in weight_matches:
        font_weights[weight] += 1
    
    return {
        "families": fonts.most_common(10),
        "sizes": font_sizes.most_common(15),
        "weights": font_weights.most_common(5),
    }


# ═══════════════════════════════════════════════════════════════════
# SPACING EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_spacing(html):
    """Extract spacing patterns (padding, margin, gap)"""
    spacing = {
        "padding": Counter(),
        "margin": Counter(),
        "gap": Counter(),
        "border_radius": Counter(),
    }
    
    # Padding
    for val in re.findall(r'padding:\s*([^;"}]+)', html):
        spacing["padding"][val.strip()] += 1
    
    # Margin
    for val in re.findall(r'margin:\s*([^;"}]+)', html):
        spacing["margin"][val.strip()] += 1
    
    # Gap
    for val in re.findall(r'gap:\s*([^;"}]+)', html):
        spacing["gap"][val.strip()] += 1
    
    # Border radius
    for val in re.findall(r'border-radius:\s*([^;"}]+)', html):
        spacing["border_radius"][val.strip()] += 1
    
    # Convert to most common
    for key in spacing:
        spacing[key] = spacing[key].most_common(10)
    
    return spacing


# ═══════════════════════════════════════════════════════════════════
# CSS VARIABLE EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_css_variables(html):
    """Extract CSS custom properties (--var)"""
    variables = {}
    
    # CSS variables in :root or anywhere
    var_matches = re.findall(r'--([\w-]+):\s*([^;"}]+)', html)
    for name, value in var_matches:
        variables[name.strip()] = value.strip()
    
    return variables


# ═══════════════════════════════════════════════════════════════════
# BREAKPOINT DETECTOR
# ═══════════════════════════════════════════════════════════════════

def extract_breakpoints(html):
    """Detect responsive breakpoints from media queries"""
    breakpoints = Counter()
    
    # @media queries
    media_matches = re.findall(r'@media\s*\([^)]+\)', html)
    for media in media_matches:
        # Extract pixel value
        px_match = re.search(r'(\d+)px', media)
        if px_match:
            breakpoints[f"{px_match.group(1)}px"] += 1
    
    return breakpoints.most_common(10)


# ═══════════════════════════════════════════════════════════════════
# GENERATORS
# ═══════════════════════════════════════════════════════════════════

def generate_theme_css(design_system):
    """Generate theme.css from extracted design system"""
    css = "/* Theme CSS - Generated by CSS/Style Cloner */\n"
    css += f"/* Source: {design_system['source']} */\n"
    css += f"/* Generated: {design_system['generated_at']} */\n\n"
    
    # CSS Variables
    css += ":root {\n"
    
    # Colors
    color_cats = design_system["colors_categorized"]
    
    if color_cats["backgrounds"]:
        primary_bg = color_cats["backgrounds"][0]["color"]
        css += f"  --color-bg-primary: {primary_bg};\n"
    if color_cats["text"]:
        primary_text = color_cats["text"][0]["color"]
        css += f"  --color-text-primary: {primary_text};\n"
    if color_cats["accents"]:
        primary_accent = color_cats["accents"][0]["color"]
        css += f"  --color-accent: {primary_accent};\n"
    if color_cats["borders"]:
        border_color = color_cats["borders"][0]["color"]
        css += f"  --color-border: {border_color};\n"
    
    # All colors as palette
    css += "\n  /* Color Palette */\n"
    for i, c in enumerate(design_system["colors_categorized"]["all"][:10]):
        css += f"  --color-palette-{i+1}: {c['color']};\n"
    
    # Fonts
    if design_system["fonts"]["families"]:
        primary_font = design_system["fonts"]["families"][0][0]
        css += f"\n  --font-body: '{primary_font}', sans-serif;\n"
        if len(design_system["fonts"]["families"]) > 1:
            heading_font = design_system["fonts"]["families"][1][0]
            css += f"  --font-heading: '{heading_font}', sans-serif;\n"
        else:
            css += f"  --font-heading: '{primary_font}', sans-serif;\n"
    
    # Font sizes
    css += "\n  /* Font Sizes */\n"
    for i, (size, count) in enumerate(design_system["fonts"]["sizes"][:6]):
        css += f"  --font-size-{i+1}: {size};\n"
    
    # Spacing
    css += "\n  /* Spacing */\n"
    if design_system["spacing"]["padding"]:
        for i, (val, count) in enumerate(design_system["spacing"]["padding"][:5]):
            css += f"  --spacing-{i+1}: {val};\n"
    
    # Border radius
    if design_system["spacing"]["border_radius"]:
        radius = design_system["spacing"]["border_radius"][0][0]
        css += f"\n  --border-radius: {radius};\n"
    
    # CSS Variables from source
    if design_system["css_variables"]:
        css += "\n  /* Original CSS Variables */\n"
        for name, value in design_system["css_variables"].items():
            css += f"  --{name}: {value};\n"
    
    css += "}\n\n"
    
    # Base styles
    css += "/* Base Styles */\n"
    css += "body {\n"
    css += "  font-family: var(--font-body);\n"
    css += "  color: var(--color-text-primary);\n"
    css += "  background: var(--color-bg-primary);\n"
    css += "  line-height: 1.6;\n"
    css += "}\n\n"
    
    css += "h1, h2, h3, h4, h5, h6 {\n"
    css += "  font-family: var(--font-heading);\n"
    css += "  color: var(--color-text-primary);\n"
    css += "}\n\n"
    
    css += "a {\n"
    css += "  color: var(--color-accent);\n"
    css += "  text-decoration: none;\n"
    css += "}\n\n"
    
    css += "a:hover {\n"
    css += "  text-decoration: underline;\n"
    css += "}\n\n"
    
    css += "button, .btn {\n"
    css += "  background: var(--color-accent);\n"
    css += "  color: var(--color-bg-primary);\n"
    css += "  border: none;\n"
    css += "  padding: var(--spacing-2, 0.5rem) var(--spacing-3, 1rem);\n"
    css += "  border-radius: var(--border-radius, 4px);\n"
    css += "  cursor: pointer;\n"
    css += "}\n\n"
    
    # Breakpoints
    if design_system["breakpoints"]:
        css += "/* Responsive Breakpoints */\n"
        for bp, count in design_system["breakpoints"]:
            css += f"/* {bp} (used {count}x) */\n"
    
    return css


def generate_settings_schema(design_system):
    """Generate Shopify settings_schema.json from extracted design system"""
    settings = [{
        "name": "theme_info",
        "theme_name": "Cloned Theme",
        "theme_version": "1.0.0",
        "theme_author": "CSS Style Cloner",
        "theme_documentation_url": "https://example.com",
        "theme_support_url": "https://example.com"
    }]
    
    # Colors section
    color_settings = {"name": "Colors", "settings": []}
    
    color_cats = design_system["colors_categorized"]
    if color_cats["backgrounds"]:
        color_settings["settings"].append({
            "type": "color",
            "id": "color_background",
            "label": "Background Color",
            "default": color_cats["backgrounds"][0]["color"]
        })
    if color_cats["text"]:
        color_settings["settings"].append({
            "type": "color",
            "id": "color_text",
            "label": "Text Color",
            "default": color_cats["text"][0]["color"]
        })
    if color_cats["accents"]:
        color_settings["settings"].append({
            "type": "color",
            "id": "color_accent",
            "label": "Accent Color",
            "default": color_cats["accents"][0]["color"]
        })
    if color_cats["borders"]:
        color_settings["settings"].append({
            "type": "color",
            "id": "color_border",
            "label": "Border Color",
            "default": color_cats["borders"][0]["color"]
        })
    
    settings.append(color_settings)
    
    # Typography section
    type_settings = {"name": "Typography", "settings": []}
    
    if design_system["fonts"]["families"]:
        type_settings["settings"].append({
            "type": "text",
            "id": "font_body",
            "label": "Body Font Family",
            "default": design_system["fonts"]["families"][0][0]
        })
        if len(design_system["fonts"]["families"]) > 1:
            type_settings["settings"].append({
                "type": "text",
                "id": "font_heading",
                "label": "Heading Font Family",
                "default": design_system["fonts"]["families"][1][0]
            })
    
    if design_system["fonts"]["sizes"]:
        type_settings["settings"].append({
            "type": "text",
            "id": "font_size_base",
            "label": "Base Font Size",
            "default": design_system["fonts"]["sizes"][0][0]
        })
    
    settings.append(type_settings)
    
    # Spacing section
    spacing_settings = {"name": "Spacing", "settings": []}
    if design_system["spacing"]["border_radius"]:
        spacing_settings["settings"].append({
            "type": "text",
            "id": "border_radius",
            "label": "Border Radius",
            "default": design_system["spacing"]["border_radius"][0][0]
        })
    
    if spacing_settings["settings"]:
        settings.append(spacing_settings)
    
    return settings


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("CSS/STYLE CLONER")
        print("━" * 69)
        print()
        print("Usage: python3 css-style-cloner.py <input-dir> [output-dir]")
        print("Example: python3 css-style-cloner.py ./rothys-extract ./cloned-styles")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "cloned-styles")
    
    print("CSS/STYLE CLONER")
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
    
    # Extract design system
    print("  [1/5] Extracting colors...")
    colors = extract_colors(html)
    colors_categorized = categorize_colors(colors)
    
    print("  [2/5] Extracting fonts...")
    fonts = extract_fonts(html)
    
    print("  [3/5] Extracting spacing...")
    spacing = extract_spacing(html)
    
    print("  [4/5] Extracting CSS variables...")
    css_vars = extract_css_variables(html)
    
    print("  [5/5] Detecting breakpoints...")
    breakpoints = extract_breakpoints(html)
    
    # Build design system
    design_system = {
        "source": input_dir,
        "generated_at": datetime.now().isoformat(),
        "colors_raw": dict(colors.most_common(30)),
        "colors_categorized": colors_categorized,
        "fonts": fonts,
        "spacing": spacing,
        "css_variables": css_vars,
        "breakpoints": breakpoints,
    }
    
    # Create output
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(output_dir, "design-system.json")
    with open(json_path, "w") as f:
        # Convert Counters to dicts for JSON
        ds_clean = json.loads(json.dumps(design_system, default=str))
        json.dump(ds_clean, f, indent=2)
    
    # Generate theme.css
    print("\n  Generating theme.css...")
    theme_css = generate_theme_css(design_system)
    css_path = os.path.join(output_dir, "theme.css")
    with open(css_path, "w") as f:
        f.write(theme_css)
    
    # Generate settings_schema.json
    print("  Generating settings_schema.json...")
    settings_schema = generate_settings_schema(design_system)
    schema_path = os.path.join(output_dir, "settings_schema.json")
    with open(schema_path, "w") as f:
        json.dump(settings_schema, f, indent=2)
    
    # Generate report
    md_path = os.path.join(output_dir, "STYLE-ANALYSIS.md")
    with open(md_path, "w") as f:
        f.write(f"""# Style Analysis Report

Source: {input_dir}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Color Palette

### Backgrounds
""")
        for c in colors_categorized["backgrounds"][:5]:
            f.write(f"- `{c['color']}` ({c['count']}x)\n")
        
        f.write("\n### Text Colors\n")
        for c in colors_categorized["text"][:5]:
            f.write(f"- `{c['color']}` ({c['count']}x)\n")
        
        f.write("\n### Accent Colors\n")
        for c in colors_categorized["accents"][:5]:
            f.write(f"- `{c['color']}` ({c['count']}x)\n")
        
        f.write("\n### Border Colors\n")
        for c in colors_categorized["borders"][:5]:
            f.write(f"- `{c['color']}` ({c['count']}x)\n")
        
        f.write(f"\n---\n\n## Typography\n\n### Font Families\n")
        for font, count in fonts["families"][:5]:
            f.write(f"- `{font}` ({count}x)\n")
        
        f.write("\n### Font Sizes\n")
        for size, count in fonts["sizes"][:10]:
            f.write(f"- `{size}` ({count}x)\n")
        
        f.write("\n### Font Weights\n")
        for weight, count in fonts["weights"]:
            f.write(f"- `{weight}` ({count}x)\n")
        
        f.write(f"\n---\n\n## Spacing\n\n### Padding\n")
        for val, count in spacing["padding"][:5]:
            f.write(f"- `{val}` ({count}x)\n")
        
        f.write("\n### Margin\n")
        for val, count in spacing["margin"][:5]:
            f.write(f"- `{val}` ({count}x)\n")
        
        f.write("\n### Gap\n")
        for val, count in spacing["gap"][:5]:
            f.write(f"- `{val}` ({count}x)\n")
        
        f.write("\n### Border Radius\n")
        for val, count in spacing["border_radius"][:5]:
            f.write(f"- `{val}` ({count}x)\n")
        
        if css_vars:
            f.write(f"\n---\n\n## CSS Variables\n\n")
            for name, value in css_vars.items():
                f.write(f"- `--{name}`: `{value}`\n")
        
        if breakpoints:
            f.write(f"\n---\n\n## Breakpoints\n\n")
            for bp, count in breakpoints:
                f.write(f"- `{bp}` ({count}x)\n")
        
        f.write(f"\n---\n\n## Generated Files\n\n")
        f.write(f"- `theme.css` - Complete CSS with design tokens\n")
        f.write(f"- `settings_schema.json` - Shopify theme settings\n")
        f.write(f"- `design-system.json` - Full structured data\n")
        f.write(f"- `STYLE-ANALYSIS.md` - This report\n")
    
    # Summary
    print(f"\nCSS/STYLE CLONER COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  theme.css - Generated stylesheet")
    print(f"  settings_schema.json - Shopify settings")
    print(f"  design-system.json - Full design data")
    print(f"  STYLE-ANALYSIS.md - Analysis report")
    print()
    print("DESIGN SYSTEM SUMMARY:")
    print(f"  • Unique colors: {len(colors_categorized['all'])}")
    print(f"  • Font families: {len(fonts['families'])}")
    print(f"  • Font sizes: {len(fonts['sizes'])}")
    print(f"  • CSS variables: {len(css_vars)}")
    print(f"  • Breakpoints: {len(breakpoints)}")


if __name__ == "__main__":
    main()
