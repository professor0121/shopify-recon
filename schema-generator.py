#!/usr/bin/env python3
"""
SCHEMA GENERATOR - Generate {% schema %} blocks from detected section settings
Analyzes section HTML, detects settings (images, text, colors, URLs), generates valid schema

Usage: python3 schema-generator.py <input-dir> [output-dir]
"""

import json, sys, os, re
from datetime import datetime
from bs4 import BeautifulSoup


def detect_settings(section_html):
    """Detect potential theme settings from section HTML"""
    soup = BeautifulSoup(section_html, "lxml")
    settings = []
    
    # Images image_picker
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src and not src.startswith("data:"):
            settings.append({
                "type": "image_picker",
                "id": f"image_{len(settings)+1}",
                "label": f"Image ({alt[:30]})" if alt else f"Image {len(settings)+1}",
            })
    
    # Headings text setting
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        if text and len(text) > 2:
            settings.append({
                "type": "text",
                "id": f"heading_{len(settings)+1}",
                "label": f"Heading ({h.name})",
                "default": text[:60],
            })
    
    # Links url setting
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href and not href.startswith("#") and text:
            settings.append({
                "type": "url",
                "id": f"link_{len(settings)+1}",
                "label": f"Link ({text[:20]})",
            })
            settings.append({
                "type": "text",
                "id": f"link_text_{len(settings)+1}",
                "label": f"Link Text ({text[:20]})",
                "default": text[:60],
            })
    
    # Colors from inline styles
    colors = set()
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        for match in re.finditer(r'(?:color|background-color|border-color):\s*(#[0-9a-fA-F]{3,6})', style):
            colors.add(match.group(1))
    
    for i, color in enumerate(sorted(colors)[:5]):
        settings.append({
            "type": "color",
            "id": f"color_{i+1}",
            "label": f"Color {i+1}",
            "default": color,
        })
    
    # Buttons text + url
    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        if text:
            settings.append({
                "type": "text",
                "id": f"button_text_{len(settings)+1}",
                "label": f"Button Text",
                "default": text[:60],
            })
    
    # Deduplicate by id
    seen = set()
    unique = []
    for s in settings:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    
    return unique[:15]  # Cap at 15 settings


def generate_schema(section_type, settings):
    """Generate {% schema %} JSON block"""
    schema = {
        "name": section_type.replace("_", " ").title(),
        "settings": settings,
        "presets": [{
            "name": section_type.replace("_", " ").title(),
            "category": "Reconstructed"
        }]
    }
    return json.dumps(schema, indent=2)


def main():
    if len(sys.argv) < 2:
        print("SCHEMA GENERATOR")
        print("━" * 69)
        print("Usage: python3 schema-generator.py <input-dir> [output-dir]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "schemas")
    
    html_path = os.path.join(input_dir, "homepage.html")
    with open(html_path) as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "lxml")
    sections = soup.find_all(id=re.compile(r"shopify-section-"))
    
    os.makedirs(output_dir, exist_ok=True)
    seen_types = set()
    generated = []
    
    print("SCHEMA GENERATOR")
    print("━" * 69)
    
    for section in sections:
        section_id = section.get("id", "")
        type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+$', section_id) or re.search(r'shopify-section-(\w+)$', section_id)
        section_type = type_match.group(1) if type_match else "unknown"
        
        if section_type in seen_types:
            continue
        seen_types.add(section_type)
        
        section_html = str(section)[:10000]
        settings = detect_settings(section_html)
        schema_json = generate_schema(section_type, settings)
        
        # Save schema file
        schema_path = os.path.join(output_dir, f"{section_type}.schema.json")
        with open(schema_path, "w") as f:
            f.write(schema_json)
        
        generated.append({"type": section_type, "settings": len(settings)})
        print(f"  • {section_type}: {len(settings)} settings detected")
    
    print(f"\n{len(generated)} schema files generated in {output_dir}/")


if __name__ == "__main__":
    main()
