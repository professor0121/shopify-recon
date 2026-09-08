#!/usr/bin/env python3
"""
CSS EXACT VALUES EXTRACTOR - Browser getComputedStyle() Extraction
Injects JavaScript into browser to extract EXACT computed CSS values
per element. Not estimated - actual rendered values.

Adopted from ai-website-cloner-template's extraction methodology.
Part of Shopify Recon | 2026-06-21

Usage: python3 css-exact-values.py <url> [output-dir]
       python3 css-exact-values.py https://rothys.com ./css-exact
"""

import json
import sys
import os
import re
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup


# The extraction script (adapted from ai-website-cloner SKILL.md)
EXTRACTION_SCRIPT = """
(function() {
  var results = {
    design_tokens: {},
    elements: [],
    fonts: [],
    colors: [],
    spacing: [],
  };
  
  var props = [
    'fontSize','fontWeight','fontFamily','lineHeight','letterSpacing','color',
    'textTransform','textDecoration','backgroundColor','background',
    'padding','paddingTop','paddingRight','paddingBottom','paddingLeft',
    'margin','marginTop','marginRight','marginBottom','marginLeft',
    'width','height','maxWidth','minWidth','maxHeight','minHeight',
    'display','flexDirection','justifyContent','alignItems','gap',
    'gridTemplateColumns','gridTemplateRows',
    'borderRadius','border','borderTop','borderBottom','borderLeft','borderRight',
    'boxShadow','overflow','overflowX','overflowY',
    'position','top','right','bottom','left','zIndex',
    'opacity','transform','transition','cursor',
    'objectFit','objectPosition','mixBlendMode','filter','backdropFilter',
    'whiteSpace','textOverflow','WebkitLineClamp'
  ];
  
  function extractStyles(el) {
    var cs = window.getComputedStyle(el);
    var styles = {};
    props.forEach(function(p) {
      var v = cs[p];
      if (v && v !== 'none' && v !== 'normal' && v !== 'auto' && v !== '0px' && v !== 'rgba(0, 0, 0, 0)') {
        styles[p] = v;
      }
    });
    return styles;
  }
  
  // Extract design tokens from :root / body
  var root = document.documentElement;
  var body = document.body;
  
  // CSS Custom Properties
  var cssVars = {};
  for (var i = 0; i < root.style.length; i++) {
    var prop = root.style[i];
    if (prop.startsWith('--')) {
      cssVars[prop] = root.style.getPropertyValue(prop);
    }
  }
  results.design_tokens.css_variables = cssVars;
  
  // Body defaults
  results.design_tokens.body = extractStyles(body);
  
  // Headings
  for (var h = 1; h <= 6; h++) {
    var heading = document.querySelector('h' + h);
    if (heading) {
      results.design_tokens['h' + h] = extractStyles(heading);
    }
  }
  
  // Links
  var link = document.querySelector('a');
  if (link) results.design_tokens.link = extractStyles(link);
  
  // Buttons
  var btn = document.querySelector('button, .btn, [class*="button"]');
  if (btn) results.design_tokens.button = extractStyles(btn);
  
  // Inputs
  var input = document.querySelector('input, textarea, select');
  if (input) results.design_tokens.input = extractStyles(input);
  
  // Extract all unique colors
  var colorSet = new Set();
  var fontSet = new Set();
  var elements = document.querySelectorAll('*');
  
  for (var i = 0; i < elements.length && i < 500; i++) {
    var el = elements[i];
    var cs = window.getComputedStyle(el);
    
    if (cs.color && cs.color !== 'rgba(0, 0, 0, 0)') colorSet.add(cs.color);
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') colorSet.add(cs.backgroundColor);
    if (cs.fontFamily) fontSet.add(cs.fontFamily);
  }
  
  results.colors = Array.from(colorSet).slice(0, 50);
  results.fonts = Array.from(fontSet).slice(0, 20);
  
  // Extract key elements with full styles
  var selectors = [
    'header', 'nav', 'footer',
    'h1', 'h2', 'h3', 'p', 'a', 'button',
    '.btn', '.product-card', '.cart-icon', '.search-input',
    '[class*="hero"]', '[class*="banner"]', '[class*="product"]',
    '[class*="collection"]', '[class*="featured"]',
    'img', 'form', 'input', 'select', 'textarea'
  ];
  
  selectors.forEach(function(sel) {
    var els = document.querySelectorAll(sel);
    for (var i = 0; i < els.length && i < 3; i++) {
      var el = els[i];
      var styles = extractStyles(el);
      if (Object.keys(styles).length > 0) {
        results.elements.push({
          selector: sel,
          index: i,
          tag: el.tagName.toLowerCase(),
          classes: el.className.toString().split(' ').slice(0, 5).join(' '),
          text: el.textContent.trim().slice(0, 100),
          styles: styles,
        });
      }
    }
  });
  
  return JSON.stringify(results, null, 2);
})();
"""


def generate_extraction_html(url):
    """Generate an HTML file that runs extraction and outputs results"""
    
    # Use string concatenation to avoid f-string issues with JS braces
    html = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n'
    html += '<title>CSS Extraction</title>\n</head>\n<body>\n'
    html += '<iframe id="target" src="' + url + '" style="width:100%;height:100vh;border:none;" onload="runExtraction()"></iframe>\n'
    html += '<script>\nfunction runExtraction() {\n'
    html += '  try {\n'
    html += '    var iframe = document.getElementById("target");\n'
    html += '    var doc = iframe.contentDocument || iframe.contentWindow.document;\n'
    html += '    var results = { design_tokens: {}, elements: [], fonts: [], colors: [] };\n'
    html += '    var props = ["fontSize","fontWeight","fontFamily","lineHeight","letterSpacing","color","backgroundColor","background","padding","margin","width","height","maxWidth","display","flexDirection","justifyContent","alignItems","gap","borderRadius","border","boxShadow","position","zIndex","opacity","transform","transition","cursor"];\n'
    html += '    function extractStyles(el) {\n'
    html += '      var cs = window.getComputedStyle(el);\n'
    html += '      var styles = {};\n'
    html += '      props.forEach(function(p) {\n'
    html += '        var v = cs[p];\n'
    html += '        if (v && v !== "none" && v !== "normal" && v !== "auto" && v !== "0px" && v !== "rgba(0, 0, 0, 0)") {\n'
    html += '          styles[p] = v;\n'
    html += '        }\n'
    html += '      });\n'
    html += '      return styles;\n'
    html += '    }\n'
    html += '    results.design_tokens.body = extractStyles(doc.body);\n'
    html += '    var selectors = ["header","nav","footer","h1","h2","h3","p","a","button",".btn","img","form","input"];\n'
    html += '    selectors.forEach(function(sel) {\n'
    html += '      var els = doc.querySelectorAll(sel);\n'
    html += '      for (var i = 0; i < els.length && i < 3; i++) {\n'
    html += '        var el = els[i];\n'
    html += '        var styles = extractStyles(el);\n'
    html += '        if (Object.keys(styles).length > 0) {\n'
    html += '          results.elements.push({ selector: sel, tag: el.tagName.toLowerCase(), classes: el.className.toString().split(" ").slice(0, 5).join(" "), text: el.textContent.trim().slice(0, 100), styles: styles });\n'
    html += '        }\n'
    html += '      }\n'
    html += '    });\n'
    html += '    var colorSet = new Set();\n'
    html += '    var fontSet = new Set();\n'
    html += '    var elements = doc.querySelectorAll("*");\n'
    html += '    for (var i = 0; i < elements.length && i < 300; i++) {\n'
    html += '      var cs = window.getComputedStyle(elements[i]);\n'
    html += '      if (cs.color) colorSet.add(cs.color);\n'
    html += '      if (cs.backgroundColor && cs.backgroundColor !== "rgba(0, 0, 0, 0)") colorSet.add(cs.backgroundColor);\n'
    html += '      if (cs.fontFamily) fontSet.add(cs.fontFamily);\n'
    html += '    }\n'
    html += '    results.colors = Array.from(colorSet).slice(0, 50);\n'
    html += '    results.fonts = Array.from(fontSet).slice(0, 20);\n'
    html += '    document.title = "CSS_EXTRACTION_RESULTS";\n'
    html += '    var output = doc.createElement("pre");\n'
    html += '    output.id = "results";\n'
    html += '    output.textContent = JSON.stringify(results, null, 2);\n'
    html += '    doc.body.appendChild(output);\n'
    html += '  } catch(e) {\n'
    html += '    document.title = "EXTRACTION_ERROR";\n'
    html += '    document.body.innerHTML = "<pre>Error: " + e.message + "\\n\\nNote: Cross-origin restriction. Use server-side fallback.</pre>";\n'
    html += '  }\n'
    html += '}\n</script>\n</body>\n</html>'
    
    return html


def extract_from_html(html, url=""):
    """Extract CSS values from HTML using BeautifulSoup (fallback method)
    This parses inline styles + <style> blocks since we can't run getComputedStyle server-side"""
    
    soup = BeautifulSoup(html, "lxml")
    
    results = {
        "extraction_method": "html_parse_fallback",
        "note": "Server-side extraction from inline styles + <style> blocks. For exact getComputedStyle values, use --browser mode.",
        "design_tokens": {},
        "elements": [],
        "colors": set(),
        "fonts": set(),
    }
    
    # Extract from <style> blocks
    style_blocks = soup.find_all("style")
    all_css = "\n".join(s.string or "" for s in style_blocks)
    
    # CSS variables from :root
    root_match = re.search(r':root\s*\{([^}]*)\}', all_css)
    if root_match:
        css_vars = {}
        for prop_match in re.finditer(r'(--[\w-]+)\s*:\s*([^;]+)', root_match.group(1)):
            css_vars[prop_match.group(1)] = prop_match.group(2).strip()
        results["design_tokens"]["css_variables"] = css_vars
    
    # Extract colors from CSS
    color_patterns = [
        r'#[0-9a-fA-F]{3,8}\b',
        r'rgba?\([^)]+\)',
        r'hsla?\([^)]+\)',
    ]
    for pattern in color_patterns:
        for match in re.finditer(pattern, all_css):
            results["colors"].add(match.group())
    
    # Extract fonts
    for match in re.finditer(r'font-family:\s*([^;}"\']+)', all_css):
        font = match.group(1).strip().rstrip(',').strip("'\"")
        primary = font.split(',')[0].strip().strip("'\"")
        results["fonts"].add(primary)
    
    # Extract element styles from inline style attributes
    for el in soup.find_all(style=True):
        style_str = el.get("style", "")
        styles = {}
        for prop in style_str.split(";"):
            if ":" in prop:
                key, value = prop.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in styles:
                    styles[key] = value
        
        if styles:
            tag = el.name
            classes = " ".join(el.get("class", []))
            text = el.get_text(strip=True)[:100]
            
            results["elements"].append({
                "selector": f"{tag}.{classes}" if classes else tag,
                "tag": tag,
                "classes": classes,
                "text": text,
                "styles": styles,
                "source": "inline_style",
            })
    
    # Extract from CSS rules (selector { property: value })
    rule_pattern = re.compile(r'([^{]+)\{([^}]*)\}', re.DOTALL)
    for match in rule_pattern.finditer(all_css):
        selector = match.group(1).strip()
        body = match.group(2)
        
        # Only process key selectors
        if any(s in selector for s in ['body', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'button', '.btn', 'header', 'nav', 'footer', 'img', ':root']):
            styles = {}
            for prop in body.split(";"):
                if ":" in prop:
                    key, value = prop.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        styles[key] = value
            
            if styles:
                results["design_tokens"][selector] = styles
    
    # Convert sets to sorted lists
    results["colors"] = sorted(results["colors"])
    results["fonts"] = sorted(results["fonts"])
    
    return results


def generate_theme_css_from_exact(extracted_data):
    """Generate theme.css from extracted exact values"""
    
    css = "/* theme.css - Generated from EXACT extracted CSS values */\n"
    css += f"/* Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} */\n"
    css += f"/* Method: {extracted_data.get('extraction_method', 'unknown')} */\n\n"
    
    # CSS Variables
    css_vars = extracted_data.get("design_tokens", {}).get("css_variables", {})
    if css_vars:
        css += ":root {\n"
        for name, value in css_vars.items():
            css += f"  {name}: {value};\n"
        css += "}\n\n"
    
    # Design tokens
    for selector, styles in extracted_data.get("design_tokens", {}).items():
        if selector == "css_variables":
            continue
        if isinstance(styles, dict) and styles:
            css += f"{selector} {{\n"
            for prop, value in styles.items():
                css += f"  {prop}: {value};\n"
            css += "}\n\n"
    
    # Colors as palette
    colors = extracted_data.get("colors", [])
    if colors:
        css += "/* Color Palette */\n"
        for i, color in enumerate(colors[:20], 1):
            css += f"/* --palette-{i}: {color} */\n"
        css += "\n"
    
    return css


def main():
    if len(sys.argv) < 2:
        print("CSS EXACT VALUES EXTRACTOR")
        print("━" * 69)
        print()
        print("Usage: python3 css-exact-values.py <url|input-dir> [output-dir]")
        print()
        print("Examples:")
        print("  python3 css-exact-values.py https://rothys.com ./css-output")
        print("  python3 css-exact-values.py ./rothys-extract ./css-output")
        sys.exit(1)
    
    target = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./css-exact-output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("CSS EXACT VALUES EXTRACTOR")
    print("━" * 69)
    
    # Determine if target is URL or directory
    if target.startswith("http") or not os.path.isdir(target):
        # URL mode - fetch HTML
        url = target if target.startswith("http") else "https://" + target
        print(f"  URL: {url}")
        
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             "--max-time", "20", url],
            capture_output=True, text=True
        )
        html = result.stdout
    else:
        # Directory mode - load homepage.html
        html_path = os.path.join(target, "homepage.html")
        if not os.path.exists(html_path):
            print(f"No homepage.html in {target}")
            sys.exit(1)
        with open(html_path) as f:
            html = f.read()
        url = ""
    
    print(f"  HTML: {len(html)} bytes")
    print()
    
    # Extract
    print("  Extracting CSS values...")
    extracted = extract_from_html(html, url)
    
    print(f"    CSS variables: {len(extracted['design_tokens'].get('css_variables', {}))}")
    print(f"    Colors: {len(extracted['colors'])}")
    print(f"    Fonts: {len(extracted['fonts'])}")
    print(f"    Elements with styles: {len(extracted['elements'])}")
    
    # Save JSON
    json_path = os.path.join(output_dir, "css-exact-values.json")
    with open(json_path, "w") as f:
        json.dump(extracted, f, indent=2, default=str)
    
    # Generate theme.css
    print("\n  Generating theme.css from exact values...")
    theme_css = generate_theme_css_from_exact(extracted)
    css_path = os.path.join(output_dir, "theme-exact.css")
    with open(css_path, "w") as f:
        f.write(theme_css)
    
    # Generate extraction HTML for browser mode
    if url:
        browser_html = generate_extraction_html(url)
        browser_path = os.path.join(output_dir, "browser-extraction.html")
        with open(browser_path, "w") as f:
            f.write(browser_html)
    
    # Summary
    print(f"\nCSS EXTRACTION COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  css-exact-values.json - Full extracted data")
    print(f"  theme-exact.css - CSS from exact values")
    if url:
        print(f"  browser-extraction.html - Open in browser for getComputedStyle()")
    print()
    print(f"EXTRACTED:")
    print(f"  • CSS Variables:     {len(extracted['design_tokens'].get('css_variables', {}))}")
    print(f"  • Design Tokens:     {len(extracted['design_tokens']) - 1}")
    print(f"  • Colors:            {len(extracted['colors'])}")
    print(f"  • Fonts:             {len(extracted['fonts'])}")
    print(f"  • Styled Elements:   {len(extracted['elements'])}")
    print()
    
    if extracted["colors"]:
        print(f"TOP COLORS:")
        for color in extracted["colors"][:10]:
            print(f"  • {color}")
    
    if extracted["fonts"]:
        print(f"\nFONTS:")
        for font in extracted["fonts"][:5]:
            print(f"  • {font}")


if __name__ == "__main__":
    main()
