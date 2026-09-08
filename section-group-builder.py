#!/usr/bin/env python3
"""
Section-Group Builder - Maps detected sections to Shopify section-groups in theme.liquid.
Generates layout/theme.liquid + section-groups/*.json
"""
import json, re, sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 section-group-builder.py <extracted_dir>")
        sys.exit(1)
    
    extracted_dir = Path(sys.argv[1])
    print("=" * 60)
    print("Section-Group Builder")
    print("=" * 60)
    
    # Find sections
    sections_dir = extracted_dir / "analysis" / "sections-reconstructed"
    if not sections_dir.exists():
        sections_dir = extracted_dir / "theme" / "sections"
    
    sections = list(sections_dir.glob("*.liquid")) if sections_dir.exists() else []
    print(f"Sections found: {len(sections)}")
    for s in sections:
        print(f"  - {s.name}")
    
    # Create theme directories
    layout_dir = extracted_dir / "theme" / "layout"
    section_groups_dir = extracted_dir / "theme" / "section-groups"
    layout_dir.mkdir(parents=True, exist_ok=True)
    section_groups_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate theme.liquid
    theme_liquid = """<!doctype html>
<html lang="{{ request.locale.iso_code }}" class="no-js">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    {%- if page_description -%}
      <meta name="description" content="{{ page_description }}">
    {%- endif -%}
    
    <link rel="canonical" href="{{ canonical_url }}">
    
    {%- if settings.favicon != blank -%}
      <link rel="icon" type="image/png" href="{{ settings.favicon | image_url: width: 32, height: 32 }}">
    {%- endif -%}
    
    <title>{{ page_title }}{% if current_tags %} &ndash; {{ 'general.meta.tags' | t: tags: current_tags | join: ', ' }}{% endif %}{% if current_page != 1 %} &ndash; {{ 'general.meta.page' | t: page: current_page }}{% endif %}{% unless page_title contains shop.name %} &ndash; {{ shop.name }}{% endunless %}</title>
    
    {{ content_for_header }}
    
    <link rel="stylesheet" href="{{ 'theme.css' | asset_url }}">
    <link rel="stylesheet" href="{{ 'animations.css' | asset_url }}">
    <link rel="stylesheet" href="{{ 'responsive.css' | asset_url }}">
    
    <style>
      :root {
        --color-primary: {{ settings.color_primary }};
        --color-secondary: {{ settings.color_secondary }};
        --color-accent: {{ settings.color_accent }};
        --color-background: {{ settings.color_background }};
        --color-text: {{ settings.color_text }};
        --color-border: {{ settings.color_border }};
        --container-width: {{ settings.container_width }}px;
        --grid-gap: {{ settings.grid_gap }}px;
        --section-spacing: {{ settings.section_spacing }}px;
        --button-radius: {{ settings.button_radius }}px;
        --button-padding-x: {{ settings.button_padding_x }}px;
        --button-padding-y: {{ settings.button_padding_y }}px;
        --button-bg: {{ settings.button_bg }};
        --button-text: {{ settings.button_text }};
      }
      
      body {
        font-family: {{ settings.font_body.family }}, {{ settings.font_body.fallback_families }};
        font-size: {{ settings.body_size }}px;
        color: var(--color-text);
        background: var(--color-background);
        margin: 0;
        line-height: 1.6;
      }
      
      h1, h2, h3, h4, h5, h6 {
        font-family: {{ settings.font_heading.family }}, {{ settings.font_heading.fallback_families }};
        font-weight: {{ settings.heading_weight }};
        margin: 0 0 0.5em;
      }
      
      .container {
        max-width: var(--container-width);
        margin: 0 auto;
        padding: 0 20px;
      }
      
      .btn, button[type="submit"], .shopify-payment-button__button {
        background: var(--button-bg);
        color: var(--button-text);
        border: none;
        border-radius: var(--button-radius);
        padding: var(--button-padding-y) var(--button-padding-x);
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        transition: opacity 0.2s ease;
      }
      
      .btn:hover { opacity: 0.85; }
      
      main { min-height: 50vh; }
      
      .section-spacing { padding: var(--section-spacing) 0; }
    </style>
    
    <script>
      document.documentElement.className = document.documentElement.className.replace('no-js', 'js');
    </script>
  </head>
  
  <body>
    {% sections 'header-group' %}
    
    <main role="main">
      {{ content_for_layout }}
    </main>
    
    {% sections 'footer-group' %}
    
    <script src="{{ 'theme.js' | asset_url }}" defer></script>
    <script src="{{ 'cart.js' | asset_url }}" defer></script>
  </body>
</html>
"""
    
    theme_path = layout_dir / "theme.liquid"
    theme_path.write_text(theme_liquid, encoding='utf-8')
    print(f"\n{theme_path} ({theme_path.stat().st_size:,} bytes)")
    
    # header-group.json
    header_group = {
        "type": "header",
        "name": "Header group",
        "sections": [
            {"type": "header", "settings": {}}
        ],
        "order": ["header"]
    }
    header_path = section_groups_dir / "header-group.json"
    with open(header_path, 'w') as f:
        json.dump(header_group, f, indent=2)
    print(f"{header_path}")
    
    # footer-group.json
    footer_group = {
        "type": "footer",
        "name": "Footer group",
        "sections": [
            {"type": "footer", "settings": {}}
        ],
        "order": ["footer"]
    }
    footer_path = section_groups_dir / "footer-group.json"
    with open(footer_path, 'w') as f:
        json.dump(footer_group, f, indent=2)
    print(f"{footer_path}")
    
    print(f"\nSection groups created: 2 (header, footer)")
    print(f"theme.liquid with section-group tags generated")

if __name__ == "__main__":
    main()
