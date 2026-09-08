#!/usr/bin/env python3
"""
SMART SECTION REVERSE-ENGINEER - Reconstruct Liquid Sections from HTML
Parses rendered HTML, detects Shopify section patterns, generates .liquid files
Part of Shopify Clone Toolkit v3 | Kiro | 2026-06-21

Usage: python3 section-reverse-engineer.py <input-dir> [output-dir]
Example: python3 section-reverse-engineer.py ./rothys-extract ./reconstructed-theme
"""

import json
import sys
import os
import re
from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser


# ═══════════════════════════════════════════════════════════════════
# SECTION DETECTOR - Parse HTML for Shopify section patterns
# ═══════════════════════════════════════════════════════════════════

class SectionDetector:
    """Detect and extract Shopify sections from rendered HTML"""
    
    # Patterns to detect sections
    SECTION_PATTERNS = [
        # Shopify standard: id="shopify-section-template--...__<type>_<id>"
        re.compile(r'id="shopify-section-[^"]*?__(\w+?)_[A-Za-z0-9]+"', re.IGNORECASE),
        # Section with data-section-id
        re.compile(r'data-section-id="([^"]+)"[^>]*data-section-type="([^"]+)"', re.IGNORECASE),
        # Section with data-section-type only
        re.compile(r'data-section-type="([^"]+)"', re.IGNORECASE),
        # Shopify section wrapper
        re.compile(r'class="shopify-section[^"]*"[^>]*>(.*?)</section>', re.DOTALL),
    ]
    
    def __init__(self, html):
        self.html = html
        self.sections = []
    
    def detect_sections(self):
        """Detect all sections in the HTML"""
        sections = []
        
        # Pattern 1: shopify-section-template IDs (most reliable)
        section_pattern = re.compile(
            r'<(?:(div|section)[^>]*?)id="shopify-section-(template--\d+__)?(\w+?)_[A-Za-z0-9]+"[^>]*?class="shopify-section[^"]*"[^>]*?>(.*?)</\1>',
            re.DOTALL | re.IGNORECASE
        )
        
        # Also match self-closing or simple div wrappers
        simple_pattern = re.compile(
            r'<(?:div|section)[^>]*?id="shopify-section-(?:template--\d+__)?(\w+?)(?:_[A-Za-z0-9]+)?"[^>]*?class="shopify-section[^"]*"[^>]*?>',
            re.IGNORECASE
        )
        
        # Find all section IDs first
        section_ids = re.findall(
            r'id="(shopify-section-[^"]+)"',
            self.html
        )
        
        for sid in section_ids:
            # Extract section type from ID
            # Format: shopify-section-template--123__banner_abc123
            # Or: shopify-section-header
            type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+$', sid)
            if type_match:
                section_type = type_match.group(1)
            else:
                # Simple format: shopify-section-header
                type_match = re.search(r'shopify-section-(\w+)$', sid)
                section_type = type_match.group(1) if type_match else "unknown"
            
            # Extract the section's HTML content
            # Find the opening tag and its matching close tag
            tag_pattern = re.compile(
                r'<(\w+)[^>]*id="' + re.escape(sid) + r'"[^>]*>',
                re.IGNORECASE
            )
            match = tag_pattern.search(self.html)
            if match:
                tag_name = match.group(1)
                start_pos = match.start()
                
                # Find closing tag
                close_tag = f"</{tag_name}>"
                depth = 1
                pos = match.end()
                
                while depth > 0 and pos < len(self.html):
                    open_match = re.search(rf'<{tag_name}[\s>]', self.html[pos:], re.IGNORECASE)
                    close_match = re.search(rf'{close_tag}', self.html[pos:], re.IGNORECASE)
                    
                    if close_match and (not open_match or close_match.start() < open_match.start()):
                        depth -= 1
                        pos += close_match.end()
                    elif open_match:
                        depth += 1
                        pos += open_match.end()
                    else:
                        break
                
                section_html = self.html[start_pos:pos]
            else:
                section_html = ""
            
            sections.append({
                "id": sid,
                "type": section_type,
                "html": section_html[:5000],  # Cap at 5KB per section
                "html_length": len(section_html),
            })
        
        return sections


# ═══════════════════════════════════════════════════════════════════
# SECTION ANALYZER - Extract settings from section HTML
# ═══════════════════════════════════════════════════════════════════

def analyze_section_settings(section_html):
    """Extract potential settings from rendered HTML"""
    settings = {}
    
    # Extract images (likely section settings)
    images = re.findall(r'<img[^>]*src="([^"]+)"[^>]*>', section_html)
    if images:
        settings["images"] = images[:5]
    
    # Extract headings (likely section title setting)
    headings = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', section_html, re.DOTALL)
    if headings:
        settings["headings"] = [h.strip() for h in headings if h.strip()][:3]
    
    # Extract links/buttons
    links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', section_html, re.DOTALL)
    if links:
        settings["links"] = [{"url": url, "text": text.strip()[:50]} for url, text in links[:10] if text.strip()]
    
    # Extract inline styles (may contain dynamic settings)
    styles = re.findall(r'style="([^"]*)"', section_html)
    if styles:
        # Extract colors
        colors = set()
        for style in styles:
            color_matches = re.findall(r'(?:color|background-color|border-color):\s*(#[0-9a-fA-F]{3,6}|[a-z]+)', style)
            colors.update(color_matches)
        if colors:
            settings["colors"] = list(colors)[:10]
        
        # Extract font sizes
        font_sizes = set()
        for style in styles:
            size_matches = re.findall(r'font-size:\s*(\d+(?:\.\d+)?(?:px|rem|em))', style)
            font_sizes.update(size_matches)
        if font_sizes:
            settings["font_sizes"] = list(font_sizes)[:10]
    
    # Extract data attributes (Shopify section settings often rendered as data-*)
    data_attrs = re.findall(r'data-([\w-]+)="([^"]*)"', section_html)
    if data_attrs:
        settings["data_attributes"] = {k: v for k, v in data_attrs[:20]}
    
    # Detect product references
    product_handles = re.findall(r'/products/([a-z0-9-]+)', section_html)
    if product_handles:
        settings["product_references"] = list(set(product_handles))[:10]
    
    # Detect collection references
    collection_handles = re.findall(r'/collections/([a-z0-9-]+)', section_html)
    if collection_handles:
        settings["collection_references"] = list(set(collection_handles))[:10]
    
    return settings


# ═══════════════════════════════════════════════════════════════════
# LIQUID GENERATOR - Generate .liquid section files
# ═══════════════════════════════════════════════════════════════════

def generate_liquid_section(section_type, settings, section_html):
    """Generate a .liquid section file from detected settings"""
    
    # Build schema settings
    schema_settings = []
    
    if "headings" in settings:
        for i, heading in enumerate(settings["headings"]):
            schema_settings.append({
                "type": "text",
                "id": f"heading_{i+1}",
                "label": f"Heading {i+1}",
                "default": heading[:60]
            })
    
    if "images" in settings:
        for i, img in enumerate(settings["images"]):
            schema_settings.append({
                "type": "image_picker",
                "id": f"image_{i+1}",
                "label": f"Image {i+1}"
            })
    
    if "links" in settings:
        for i, link in enumerate(settings["links"]):
            schema_settings.append({
                "type": "url",
                "id": f"link_{i+1}",
                "label": f"Link {i+1}"
            })
            schema_settings.append({
                "type": "text",
                "id": f"link_text_{i+1}",
                "label": f"Link {i+1} Text",
                "default": link["text"][:60]
            })
    
    if "colors" in settings:
        for i, color in enumerate(settings["colors"]):
            schema_settings.append({
                "type": "color",
                "id": f"color_{i+1}",
                "label": f"Color {i+1}",
                "default": color
            })
    
    # Build schema
    schema = {
        "name": section_type.replace("_", " ").title(),
        "settings": schema_settings,
        "presets": [
            {
                "name": section_type.replace("_", " ").title(),
                "category": "Reconstructed"
            }
        ]
    }
    
    # Build Liquid HTML
    liquid_parts = []
    liquid_parts.append(f"<!-- {section_type} section - reverse-engineered from rendered HTML -->")
    liquid_parts.append(f"<!-- Detected settings: {len(schema_settings)} -->")
    liquid_parts.append("")
    
    # Generate Liquid template
    if section_type == "banner":
        liquid_parts.append('<div class="section-{{ section.id }}">')
        liquid_parts.append('  {% if section.settings.image_1 %}')
        liquid_parts.append('    <img src="{{ section.settings.image_1 | image_url: width: 2000 }}" alt="{{ section.settings.heading_1 | escape }}">')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('  {% if section.settings.heading_1 %}')
        liquid_parts.append('    <h2>{{ section.settings.heading_1 }}</h2>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('  {% if section.settings.link_1 %}')
        liquid_parts.append('    <a href="{{ section.settings.link_1 }}">{{ section.settings.link_text_1 }}</a>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('</div>')
    elif section_type == "product_carousel":
        liquid_parts.append('<div class="product-carousel-{{ section.id }}">')
        liquid_parts.append('  {% if section.settings.heading_1 %}')
        liquid_parts.append('    <h2>{{ section.settings.heading_1 }}</h2>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('  <div class="carousel">')
        liquid_parts.append('    {% assign collection = collections[section.settings.collection] %}')
        liquid_parts.append('    {% for product in collection.products limit: 8 %}')
        liquid_parts.append('      <div class="carousel-item">')
        liquid_parts.append('        <a href="{{ product.url }}">')
        liquid_parts.append('          <img src="{{ product.featured_image | image_url: width: 400 }}" alt="{{ product.title }}">')
        liquid_parts.append('          <h3>{{ product.title }}</h3>')
        liquid_parts.append('          <p>{{ product.price | money }}</p>')
        liquid_parts.append('        </a>')
        liquid_parts.append('      </div>')
        liquid_parts.append('    {% endfor %}')
        liquid_parts.append('  </div>')
        liquid_parts.append('</div>')
        # Add collection setting
        schema["settings"].insert(0, {
            "type": "collection",
            "id": "collection",
            "label": "Collection"
        })
    elif section_type == "spacer":
        liquid_parts.append('<div class="spacer-{{ section.id }}" style="height: {{ section.settings.height }}px;"></div>')
        schema["settings"].insert(0, {
            "type": "range",
            "id": "height",
            "label": "Height",
            "min": 0, "max": 200, "default": 40, "step": 5, "unit": "px"
        })
    elif section_type == "generic_text":
        liquid_parts.append('<div class="text-{{ section.id }}">')
        liquid_parts.append('  {% if section.settings.heading_1 %}')
        liquid_parts.append('    <h2>{{ section.settings.heading_1 }}</h2>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('  {% if section.settings.text %}')
        liquid_parts.append('    <div>{{ section.settings.text }}</div>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('</div>')
        schema["settings"].append({
            "type": "richtext",
            "id": "text",
            "label": "Text"
        })
    else:
        # Generic fallback
        liquid_parts.append(f'<div class="section-{section_type}">')
        liquid_parts.append('  {% if section.settings.heading_1 %}')
        liquid_parts.append('    <h2>{{ section.settings.heading_1 }}</h2>')
        liquid_parts.append('  {% endif %}')
        if "images" in settings:
            liquid_parts.append('  {% if section.settings.image_1 %}')
            liquid_parts.append('    <img src="{{ section.settings.image_1 | image_url: width: 1000 }}" alt="">')
            liquid_parts.append('  {% endif %}')
        liquid_parts.append('  {% if section.settings.link_1 %}')
        liquid_parts.append('    <a href="{{ section.settings.link_1 }}">{{ section.settings.link_text_1 }}</a>')
        liquid_parts.append('  {% endif %}')
        liquid_parts.append('</div>')
    
    liquid_parts.append("")
    liquid_parts.append("{% schema %}")
    liquid_parts.append(json.dumps(schema, indent=2))
    liquid_parts.append("{% endschema %}")
    
    return "\n".join(liquid_parts)


# ═══════════════════════════════════════════════════════════════════
# MAIN PROCESSOR
# ═══════════════════════════════════════════════════════════════════

def process_store(input_dir, output_dir):
    """Process a single store's HTML and generate Liquid sections"""
    
    # Load homepage HTML
    html_path = os.path.join(input_dir, "homepage.html")
    if not os.path.exists(html_path):
        print(f"No homepage.html found in {input_dir}")
        return None
    
    with open(html_path) as f:
        html = f.read()
    
    print(f"  HTML loaded: {len(html)} bytes")
    
    # Detect sections
    detector = SectionDetector(html)
    sections = detector.detect_sections()
    
    print(f"  Sections detected: {len(sections)}")
    
    if not sections:
        print("   No sections detected. Trying alternative patterns...")
        # Try simpler pattern
        section_ids = re.findall(r'id="(shopify-section-[^"]+)"', html)
        for sid in section_ids[:30]:
            type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+', sid) or re.search(r'shopify-section-(\w+)', sid)
            section_type = type_match.group(1) if type_match else "unknown"
            sections.append({
                "id": sid,
                "type": section_type,
                "html": "",
                "html_length": 0,
            })
        print(f"  Sections found (alt): {len(sections)}")
    
    # Create output directory
    sections_dir = os.path.join(output_dir, "sections")
    os.makedirs(sections_dir, exist_ok=True)
    
    # Process each section
    results = []
    seen_types = set()
    
    for section in sections:
        section_type = section["type"]
        
        # Skip duplicates of same type (keep first occurrence)
        if section_type in seen_types:
            continue
        seen_types.add(section_type)
        
        # Analyze settings
        settings = analyze_section_settings(section["html"])
        
        # Generate Liquid
        liquid_code = generate_liquid_section(section_type, settings, section["html"])
        
        # Save file
        filename = f"{section_type}.liquid"
        filepath = os.path.join(sections_dir, filename)
        with open(filepath, "w") as f:
            f.write(liquid_code)
        
        results.append({
            "type": section_type,
            "id": section["id"],
            "file": filename,
            "settings_count": len(settings),
            "html_size": section["html_length"],
            "settings": settings,
        })
    
    return results


def generate_report(results, output_dir, store_name="Store"):
    """Generate analysis report"""
    
    md_path = os.path.join(output_dir, "SECTION-ANALYSIS.md")
    
    with open(md_path, "w") as f:
        f.write(f"""# Section Reverse-Engineer Report

Store: {store_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Sections reconstructed: {len(results)}

---

## Reconstructed Sections

| # | Section Type | Settings | HTML Size | File |
|---|-------------|----------|-----------|------|
""")
        for i, r in enumerate(results, 1):
            f.write(f"| {i} | `{r['type']}` | {r['settings_count']} | {r['html_size']} bytes | `{r['file']}` |\n")
        
        f.write(f"\n---\n\n## Section Details\n\n")
        
        for r in results:
            f.write(f"### {r['type']}\n\n")
            f.write(f"- **Section ID:** `{r['id']}`\n")
            f.write(f"- **Settings detected:** {r['settings_count']}\n")
            
            if r["settings"]:
                for key, val in r["settings"].items():
                    if isinstance(val, list) and len(val) > 0:
                        f.write(f"- **{key}:** {val[:5]}\n")
                    else:
                        f.write(f"- **{key}:** {val}\n")
            f.write("\n")
        
        f.write(f"""---

## Generated Files

All section files saved to: `{output_dir}/sections/`

To use in Shopify theme:
1. Copy files to your theme's `sections/` directory
2. Add sections to templates via `{{% section 'section_type' %}}`
3. Customize settings in Shopify Theme Editor

---

*Generated by Smart Section Reverse-Engineer v1*
""")
    
    # Print summary
    print(f"\nSECTION REVERSE-ENGINEER COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/sections/")
    print(f"  SECTION-ANALYSIS.md - Analysis report")
    print(f"  {len(results)} .liquid section files generated")
    print()
    print("RECONSTRUCTED SECTIONS:")
    for r in results:
        print(f"  • {r['type']}.liquid - {r['settings_count']} settings detected")


def main():
    if len(sys.argv) < 2:
        print("SMART SECTION REVERSE-ENGINEER")
        print("━" * 69)
        print()
        print("Usage: python3 section-reverse-engineer.py <input-dir> [output-dir]")
        print("Example: python3 section-reverse-engineer.py ./rothys-extract ./reconstructed")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "reconstructed")
    
    print("SMART SECTION REVERSE-ENGINEER")
    print("━" * 69)
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print()
    
    results = process_store(input_dir, output_dir)
    
    if results:
        generate_report(results, output_dir, input_dir)
    else:
        print("No sections could be extracted")


if __name__ == "__main__":
    main()
