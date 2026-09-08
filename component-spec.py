#!/usr/bin/env python3
"""
COMPONENT SPEC GENERATOR - AI-Grade Component Specifications
Adopted from ai-website-cloner-template's SKILL.md methodology
Generates detailed spec files per section, ready for Liquid conversion

Usage: python3 component-spec.py <input-dir> [output-dir]
Example: python3 component-spec.py ./rothys-extract ./specs
"""

import json
import sys
import os
import re
from collections import Counter
from datetime import datetime
from bs4 import BeautifulSoup


def generate_component_spec(section_html, section_type, section_id, index, output_dir):
    """Generate a detailed spec file for a Shopify section"""
    
    soup = BeautifulSoup(section_html, "lxml")
    
    # Extract computed styles from inline styles
    styles = {}
    for el in soup.find_all(style=True):
        style_str = el.get("style", "")
        tag = el.name
        classes = " ".join(el.get("class", []))
        key = f"{tag}.{classes}" if classes else tag
        styles[key] = parse_inline_styles(style_str)
    
    # Extract text content
    texts = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "button"]):
        text = el.get_text(strip=True)
        if text and len(text) > 1:
            texts.append({
                "tag": el.name,
                "text": text[:200],
                "class": " ".join(el.get("class", [])),
            })
    
    # Extract images
    images = []
    for img in soup.find_all("img"):
        images.append({
            "src": img.get("src", "")[:200],
            "alt": img.get("alt", ""),
            "width": img.get("width", ""),
            "height": img.get("height", ""),
            "loading": img.get("loading", ""),
        })
    
    # Extract links
    links = []
    for a in soup.find_all("a", href=True):
        links.append({
            "href": a["href"][:200],
            "text": a.get_text(strip=True)[:50],
            "class": " ".join(a.get("class", [])),
        })
    
    # Detect interaction model
    interaction = detect_interaction_model(section_html)
    
    # Detect responsive behavior
    responsive = detect_responsive(section_html)
    
    # Generate spec markdown
    spec = f"""# {section_type} Section Specification

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Section ID: `{section_id}`
Index: {index}

---

## Overview
- **Section type:** `{section_type}`
- **HTML size:** {len(section_html)} bytes
- **Interaction model:** {interaction['model']}
- **Has forms:** {'Yes' if '<form' in section_html.lower() else 'No'}
- **Has images:** {'Yes' if images else 'No'}
- **Has links:** {'Yes' if links else 'No'}

---

## DOM Structure
"""
    
    # Build DOM tree summary
    dom_tree = build_dom_tree(soup, max_depth=4)
    spec += "```\n" + dom_tree + "\n```\n\n"
    
    # Styles
    spec += "## Computed Styles (from inline styles)\n\n"
    if styles:
        for selector, props in styles.items():
            spec += f"### `{selector}`\n"
            for prop, value in props.items():
                spec += f"- `{prop}: {value}`\n"
            spec += "\n"
    else:
        spec += "No inline styles detected. Styles come from external CSS.\n\n"
    
    # Text content
    spec += "## Text Content (verbatim)\n\n"
    if texts:
        for t in texts:
            spec += f"- `<{t['tag']}>` ({t['class']}): \"{t['text']}\"\n"
    else:
        spec += "No text content found.\n"
    spec += "\n"
    
    # Images
    spec += "## Assets\n\n"
    if images:
        spec += "### Images\n\n"
        for i, img in enumerate(images, 1):
            spec += f"{i}. `{img['src']}`\n"
            spec += f"   - alt: \"{img['alt']}\"\n"
            spec += f"   - dimensions: {img['width']}x{img['height']}\n"
            spec += f"   - loading: {img['loading']}\n"
    else:
        spec += "No images in this section.\n"
    spec += "\n"
    
    # Links
    spec += "### Links\n\n"
    if links:
        for l in links:
            spec += f"- `{l['href']}` \"{l['text']}\" ({l['class']})\n"
    else:
        spec += "No links in this section.\n"
    spec += "\n"
    
    # Interaction model
    spec += f"""---

## States & Behaviors

### Interaction Model: {interaction['model']}
"""
    if interaction["details"]:
        for detail in interaction["details"]:
            spec += f"- {detail}\n"
    
    if interaction["hover_effects"]:
        spec += "\n### Hover Effects\n\n"
        for hover in interaction["hover_effects"]:
            spec += f"- `{hover}`\n"
    
    if interaction["transitions"]:
        spec += "\n### Transitions\n\n"
        for trans in interaction["transitions"]:
            spec += f"- `{trans}`\n"
    
    if interaction["animations"]:
        spec += "\n### Animations\n\n"
        for anim in interaction["animations"]:
            spec += f"- `{anim}`\n"
    
    spec += "\n"
    
    # Responsive
    spec += f"""---

## Responsive Behavior

"""
    if responsive["breakpoints"]:
        for bp, count in responsive["breakpoints"]:
            spec += f"- Breakpoint `{bp}` ({count} rules)\n"
    else:
        spec += "No responsive breakpoints detected in inline styles.\n"
    
    spec += f"""
---

## Liquid Conversion Guide

### Suggested Liquid Structure
```liquid
<!-- sections/{section_type}.liquid -->
<div class="section-{section_type} {{ section.settings.custom_class }}">
  {{ section.settings.content }}
</div>

{{ '% schema %' }}
{{
  "name": "{section_type.replace('_', ' ').title()}",
  "settings": [
    // Add settings based on extracted content
  ],
  "presets": [
    {{"name": "{section_type.replace('_', ' ').title()}"}}
  ]
}}
{{ '% endschema %' }}
```

### CSS Classes to Implement
"""
    
    # Extract unique CSS classes
    all_classes = set()
    for el in soup.find_all(class_=True):
        for cls in el.get("class", []):
            all_classes.add(cls)
    
    if all_classes:
        for cls in sorted(all_classes)[:20]:
            spec += f"- `.{cls}`\n"
    else:
        spec += "No CSS classes found.\n"
    
    # Write spec file
    spec_path = os.path.join(output_dir, f"{section_type}_{index}.spec.md")
    with open(spec_path, "w") as f:
        f.write(spec)
    
    return spec_path


def parse_inline_styles(style_str):
    """Parse inline style string into dict"""
    styles = {}
    for prop in style_str.split(";"):
        if ":" in prop:
            key, value = prop.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                styles[key] = value
    return styles


def detect_interaction_model(html):
    """Detect if section is click/scroll/hover/time driven"""
    details = []
    hover_effects = []
    transitions = []
    animations = []
    
    # Hover
    if ":hover" in html:
        hover_matches = re.findall(r'([^{]*?:hover[^{]*)\{([^}]*)\}', html)
        for selector, props in hover_matches:
            hover_effects.append(f"{selector.strip()} {props.strip()[:80]}")
    
    # Transitions
    transition_matches = re.findall(r'transition:\s*([^;}"\']+)', html)
    for t in transition_matches:
        transitions.append(t.strip())
    
    # Animations
    anim_matches = re.findall(r'animation:\s*([^;}"\']+)', html)
    for a in anim_matches:
        animations.append(a.strip())
    
    # Keyframes
    kf_matches = re.findall(r'@keyframes\s+(\w+)', html)
    animations.extend(kf_matches)
    
    # JS interactions
    if "addEventListener" in html:
        if "click" in html.lower():
            details.append("JavaScript click handler detected")
        if "scroll" in html.lower():
            details.append("JavaScript scroll handler detected")
        if "IntersectionObserver" in html:
            details.append("IntersectionObserver detected (scroll-triggered animation)")
    
    # Determine model
    has_scroll = "IntersectionObserver" in html or "scroll" in html.lower()
    has_click = "onclick" in html.lower() or "addEventListener" in html and "click" in html.lower()
    has_hover = ":hover" in html
    has_time = "setInterval" in html or "setTimeout" in html or "animation:" in html
    
    if has_scroll:
        model = "scroll-driven"
    elif has_click:
        model = "click-driven"
    elif has_time:
        model = "time-driven"
    elif has_hover:
        model = "hover-driven"
    else:
        model = "static"
    
    return {
        "model": model,
        "details": details,
        "hover_effects": hover_effects[:10],
        "transitions": list(set(transitions))[:10],
        "animations": list(set(animations))[:10],
    }


def detect_responsive(html):
    """Detect responsive breakpoints"""
    breakpoints = Counter()
    
    # Media queries
    media_matches = re.findall(r'@media\s*\([^)]*?(\d+)px', html)
    for bp in media_matches:
        breakpoints[f"{bp}px"] += 1
    
    return {"breakpoints": breakpoints.most_common(10)}


def build_dom_tree(soup, max_depth=4, indent=0):
    """Build a text representation of DOM tree"""
    result = []
    
    for child in soup.children:
        if child.name is None:
            continue
        
        classes = " ".join(child.get("class", [])) if hasattr(child, "get") else ""
        class_str = f".{classes}" if classes else ""
        
        text = child.get_text(strip=True)[:50] if hasattr(child, "get_text") else ""
        text_str = f' "{text}"' if text and len(text) > 2 else ""
        
        result.append(f"{'  ' * indent}{child.name}{class_str}{text_str}")
        
        if indent < max_depth and hasattr(child, "children"):
            inner = build_dom_tree(child, max_depth, indent + 1)
            if inner:
                result.append(inner)
    
    return "\n".join(result)


def main():
    if len(sys.argv) < 2:
        print("COMPONENT SPEC GENERATOR")
        print("━" * 69)
        print()
        print("Usage: python3 component-spec.py <input-dir> [output-dir]")
        print("Example: python3 component-spec.py ./rothys-extract ./specs")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "component-specs")
    
    print("COMPONENT SPEC GENERATOR")
    print("━" * 69)
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print()
    
    # Load homepage HTML
    html_path = os.path.join(input_dir, "homepage.html")
    if not os.path.exists(html_path):
        print(f"No homepage.html in {input_dir}")
        sys.exit(1)
    
    with open(html_path) as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "lxml")
    
    # Find all Shopify sections
    sections = soup.find_all(id=re.compile(r"shopify-section-"))
    
    if not sections:
        print("   No Shopify sections found. Generating specs for top-level elements...")
        sections = soup.find("body").find_all(recursive=False) if soup.find("body") else []
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"  Found {len(sections)} sections")
    print()
    
    specs_generated = []
    seen_types = set()
    
    for i, section in enumerate(sections):
        section_id = section.get("id", f"section-{i}")
        
        # Extract section type
        type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+$', section_id) or re.search(r'shopify-section-(\w+)$', section_id)
        section_type = type_match.group(1) if type_match else f"section_{i}"
        
        # Skip duplicates of same type
        if section_type in seen_types:
            continue
        seen_types.add(section_type)
        
        section_html = str(section)[:10000]  # Cap at 10KB
        
        print(f"  [{i+1}/{len(sections)}] Generating spec for '{section_type}'...")
        
        spec_path = generate_component_spec(section_html, section_type, section_id, i, output_dir)
        specs_generated.append({
            "type": section_type,
            "id": section_id,
            "spec_file": os.path.basename(spec_path),
        })
    
    # Save index
    index_path = os.path.join(output_dir, "SPECS-INDEX.json")
    with open(index_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_specs": len(specs_generated),
            "specs": specs_generated,
        }, f, indent=2)
    
    print(f"\nCOMPONENT SPECS GENERATED")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  {len(specs_generated)} spec files generated")
    print(f"  SPECS-INDEX.json - Index of all specs")
    print()
    print("SPECS GENERATED:")
    for s in specs_generated:
        print(f"  • {s['spec_file']} - {s['type']}")


if __name__ == "__main__":
    main()
