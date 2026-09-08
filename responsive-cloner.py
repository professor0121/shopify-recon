#!/usr/bin/env python3
"""
RESPONSIVE CLONER - Extract @media queries + Generate Responsive CSS
Extracts all breakpoints, responsive rules, mobile-specific styles
Generates: responsive.css with all breakpoints preserved

Usage: python3 responsive-cloner.py <input-dir> [output-dir]
"""

import json, sys, os, re
from collections import Counter
from datetime import datetime


def extract_media_queries(html):
    """Extract all @media query blocks from HTML"""
    # Get all CSS from <style> blocks
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(style_blocks)
    
    media_queries = []
    
    # Find @media blocks with balanced brace matching
    media_pattern = re.compile(r'@media\s+([^{]+)\s*\{', re.IGNORECASE)
    
    for match in media_pattern.finditer(all_css):
        query = match.group(1).strip()
        start = match.end()
        
        # Find matching closing brace
        depth = 1
        pos = start
        while depth > 0 and pos < len(all_css):
            if all_css[pos] == '{':
                depth += 1
            elif all_css[pos] == '}':
                depth -= 1
            pos += 1
        
        body = all_css[start:pos-1]
        
        # Extract breakpoint value
        bp_match = re.search(r'(\d+)px', query)
        breakpoint = int(bp_match.group(1)) if bp_match else 0
        
        # Count rules inside
        rule_count = len(re.findall(r'\{[^}]*\}', body))
        
        media_queries.append({
            "query": query,
            "breakpoint_px": breakpoint,
            "rule_count": rule_count,
            "body": body[:2000],
        })
    
    return media_queries


def extract_mobile_classes(html):
    """Detect mobile-specific CSS classes"""
    mobile_classes = []
    
    patterns = [
        (r'class="[^"]*\bmobile\b[^"]*"', "mobile"),
        (r'class="[^"]*\bdesktop\b[^"]*"', "desktop"),
        (r'class="[^"]*\btablet\b[^"]*"', "tablet"),
        (r'class="[^"]*\bhidden\b[^"]*"', "hidden"),
        (r'class="[^"]*\bvisible\b[^"]*"', "visible"),
        (r'class="[^"]*\bmd:hidden\b[^"]*"', "md:hidden"),
        (r'class="[^"]*\blg:block\b[^"]*"', "lg:block"),
        (r'class="[^"]*\bsm:block\b[^"]*"', "sm:block"),
    ]
    
    for pattern, label in patterns:
        count = len(re.findall(pattern, html))
        if count > 0:
            mobile_classes.append({"type": label, "count": count})
    
    return mobile_classes


def extract_viewport(html):
    """Extract viewport meta tag"""
    match = re.search(r'<meta[^>]*name="viewport"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    return match.group(1) if match else None


def generate_responsive_css(media_queries, mobile_classes):
    """Generate responsive.css with all extracted breakpoints"""
    
    css = "/* responsive.css - Extracted from competitor store */\n"
    css += f"/* Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} */\n"
    css += f"/* Media queries: {len(media_queries)} */\n\n"
    
    # Group by breakpoint
    by_breakpoint = {}
    for mq in media_queries:
        bp = mq["breakpoint_px"]
        if bp not in by_breakpoint:
            by_breakpoint[bp] = []
        by_breakpoint[bp].append(mq)
    
    # Sort breakpoints (mobile-first)
    for bp in sorted(by_breakpoint.keys()):
        if bp == 0:
            css += "/* ═══ Non-specific media queries ═══ */\n\n"
        else:
            css += f"/* ═══ Breakpoint: {bp}px ═══ */\n\n"
        
        for mq in by_breakpoint[bp]:
            css += f"@media {mq['query']} {{\n"
            css += mq["body"][:1000]
            css += "\n}\n\n"
    
    # Add mobile utility classes
    if mobile_classes:
        css += "/* ═══ Responsive Utility Classes ═══ */\n\n"
        css += ".hidden { display: none !important; }\n"
        css += ".visible { display: block !important; }\n"
        css += ".mobile-only { display: block; }\n"
        css += ".desktop-only { display: none; }\n"
        css += "\n@media (max-width: 768px) {\n"
        css += "  .mobile-only { display: block; }\n"
        css += "  .desktop-only { display: none; }\n"
        css += "}\n"
        css += "@media (min-width: 769px) {\n"
        css += "  .mobile-only { display: none; }\n"
        css += "  .desktop-only { display: block; }\n"
        css += "}\n"
    
    return css


def main():
    if len(sys.argv) < 2:
        print("RESPONSIVE CLONER")
        print("━" * 69)
        print("Usage: python3 responsive-cloner.py <input-dir> [output-dir]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "responsive")
    
    html_path = os.path.join(input_dir, "homepage.html")
    with open(html_path) as f:
        html = f.read()
    
    print("RESPONSIVE CLONER")
    print("━" * 69)
    
    viewport = extract_viewport(html)
    media_queries = extract_media_queries(html)
    mobile_classes = extract_mobile_classes(html)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    analysis = {
        "viewport": viewport,
        "media_queries_count": len(media_queries),
        "breakpoints": sorted(set(mq["breakpoint_px"] for mq in media_queries if mq["breakpoint_px"] > 0)),
        "mobile_classes": mobile_classes,
        "media_queries": [{"query": mq["query"], "breakpoint": mq["breakpoint_px"], "rules": mq["rule_count"]} for mq in media_queries],
    }
    
    with open(os.path.join(output_dir, "responsive-analysis.json"), "w") as f:
        json.dump(analysis, f, indent=2)
    
    # Generate responsive.css
    css = generate_responsive_css(media_queries, mobile_classes)
    with open(os.path.join(output_dir, "responsive.css"), "w") as f:
        f.write(css)
    
    print(f"  Viewport: {viewport}")
    print(f"  Media queries: {len(media_queries)}")
    print(f"  Breakpoints: {analysis['breakpoints']}")
    print(f"  Mobile classes: {len(mobile_classes)}")
    print(f"\nresponsive.css generated ({len(css)} bytes)")


if __name__ == "__main__":
    main()
