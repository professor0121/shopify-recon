#!/usr/bin/env python3
"""
SMART ASSET REPLACER - Replace ALL CDN URLs with Local Paths
Scans every theme file (.liquid, .css, .js, .json) and replaces
external CDN URLs with local asset paths
Part of Shopify Recon | 2026-06-21

Usage: python3 asset-replacer.py <theme-dir> <url-mapping.json>
Example: python3 asset-replacer.py ./theme ./url-mapping.json
"""

import json
import sys
import os
import re
from datetime import datetime
from collections import Counter


def load_mapping(mapping_path):
    """Load URL local path mapping"""
    with open(mapping_path) as f:
        return json.load(f)


def replace_in_file(filepath, mapping, replacements):
    """Replace all CDN URLs in a single file"""
    
    with open(filepath, "r", errors="ignore") as f:
        content = f.read()
    
    original = content
    file_replacements = 0
    
    for url, local_path in mapping.items():
        if url in content:
            # Normalize path for Shopify Liquid
            # CSS/JS: {{ 'file.css' | asset_url }}
            # Images: {{ 'file.jpg' | asset_url }}
            
            filename = os.path.basename(local_path)
            ext = os.path.splitext(filename)[1].lower()
            
            # Determine Liquid asset reference
            if ext in ['.css']:
                liquid_ref = "{{ '" + filename + "' | asset_url | stylesheet_tag }}"
            elif ext in ['.js']:
                liquid_ref = "{{ '" + filename + "' | asset_url }}"
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico']:
                # For images, use asset_url directly
                liquid_ref = "{{ '" + filename + "' | asset_url }}"
            else:
                liquid_ref = "{{ '" + filename + "' | asset_url }}"
            
            # Replace URL in various contexts
            # 1. In CSS url()
            content = content.replace(f"url({url})", f"url({liquid_ref})")
            content = content.replace(f"url('{url}')", f"url({liquid_ref})")
            content = content.replace(f'url("{url}")', f"url({liquid_ref})")
            
            # 2. In HTML src attributes
            content = content.replace(f'src="{url}"', f'src="{liquid_ref}"')
            content = content.replace(f"src='{url}'", f"src='{liquid_ref}'")
            
            # 3. In CSS background-image
            content = content.replace(f"background-image: url({url})", f"background-image: url({liquid_ref})")
            content = content.replace(f"background-image: url('{url}')", f"background-image: url({liquid_ref})")
            
            # 4. In href attributes
            content = content.replace(f'href="{url}"', f'href="{liquid_ref}"')
            content = content.replace(f"href='{url}'", f"href='{liquid_ref}'")
            
            # 5. In meta content
            content = content.replace(f'content="{url}"', f'content="{liquid_ref}"')
            
            # 6. Raw URL in JSON/JS
            content = content.replace(f'"{url}"', f'"{liquid_ref}"')
            content = content.replace(f"'{url}'", f"'{liquid_ref}'")
            
            # 7. URL with protocol variations
            if url.startswith("https://"):
                http_url = "http://" + url[8:]
                content = content.replace(f'"{http_url}"', f'"{liquid_ref}"')
                content = content.replace(f"'{http_url}'", f"'{liquid_ref}'")
            
            # 8. Protocol-relative URLs
            if url.startswith("https://"):
                rel_url = "//" + url[8:]
                content = content.replace(f'"{rel_url}"', f'"{liquid_ref}"')
                content = content.replace(f"'{rel_url}'", f"'{liquid_ref}'")
                content = content.replace(f"url({rel_url})", f"url({liquid_ref})")
            
            count = original.count(url) - content.count(url)
            if count > 0:
                file_replacements += count
    
    # Write back if changed
    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
    
    return file_replacements


def scan_theme(theme_dir, mapping):
    """Scan all theme files and replace URLs"""
    
    extensions = [".liquid", ".css", ".js", ".json", ".html", ".htm"]
    results = {
        "files_scanned": 0,
        "files_modified": 0,
        "total_replacements": 0,
        "by_file": [],
        "by_extension": Counter(),
    }
    
    for root, dirs, files in os.walk(theme_dir):
        # Skip .git, node_modules
        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]
        
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()
            
            if ext not in extensions:
                continue
            
            results["files_scanned"] += 1
            results["by_extension"][ext] += 1
            
            replacements = replace_in_file(filepath, mapping, results)
            
            if replacements > 0:
                results["files_modified"] += 1
                results["total_replacements"] += replacements
                rel_path = os.path.relpath(filepath, theme_dir)
                results["by_file"].append({
                    "file": rel_path,
                    "replacements": replacements,
                })
    
    return results


def generate_report(results, theme_dir, mapping_count, output_path):
    """Generate replacement report"""
    
    with open(output_path, "w") as f:
        f.write(f"""# Asset Replacement Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Theme: {theme_dir}
URL mappings: {mapping_count}

---

## Summary

| Metric | Value |
|--------|-------|
| Files Scanned | {results['files_scanned']} |
| Files Modified | {results['files_modified']} |
| Total Replacements | {results['total_replacements']} |
| Replacement Rate | {results['total_replacements']/results['files_scanned']:.1f} per file |

---

## Files by Extension

| Extension | Count |
|-----------|-------|
""")
        for ext, count in results["by_extension"].most_common():
            f.write(f"| {ext} | {count} |\n")
        
        f.write(f"\n---\n\n## Modified Files\n\n")
        for item in sorted(results["by_file"], key=lambda x: x["replacements"], reverse=True):
            f.write(f"- `{item['file']}` - {item['replacements']} replacements\n")
        
        f.write(f"\n---\n\n## Status\n\n")
        if results["total_replacements"] > 0:
            f.write(f"**{results['total_replacements']} CDN URLs replaced with local Liquid asset references.**\n\n")
            f.write("Theme now loads assets from local files instead of competitor CDN.\n")
        else:
            f.write("No CDN URLs found to replace. Theme may already use local assets.\n")


def main():
    if len(sys.argv) < 3:
        print("SMART ASSET REPLACER")
        print("━" * 69)
        print()
        print("Usage: python3 asset-replacer.py <theme-dir> <url-mapping.json>")
        print("Example: python3 asset-replacer.py ./theme ./url-mapping.json")
        sys.exit(1)
    
    theme_dir = sys.argv[1]
    mapping_path = sys.argv[2]
    
    print("SMART ASSET REPLACER")
    print("━" * 69)
    print(f"  Theme: {theme_dir}")
    print(f"  Mapping: {mapping_path}")
    print()
    
    if not os.path.exists(theme_dir):
        print(f"Theme directory not found: {theme_dir}")
        sys.exit(1)
    
    if not os.path.exists(mapping_path):
        print(f"URL mapping not found: {mapping_path}")
        sys.exit(1)
    
    # Load mapping
    mapping = load_mapping(mapping_path)
    print(f"  URL mappings loaded: {len(mapping)}")
    print()
    
    # Scan and replace
    print("  Scanning theme files...")
    results = scan_theme(theme_dir, mapping)
    
    # Generate report
    report_path = os.path.join(theme_dir, "ASSET-REPLACEMENT-REPORT.md")
    generate_report(results, theme_dir, len(mapping), report_path)
    
    # Summary
    print(f"\nASSET REPLACEMENT COMPLETE")
    print(f"━" * 69)
    print(f"  Theme: {theme_dir}")
    print(f"  ASSET-REPLACEMENT-REPORT.md - Detailed report")
    print()
    print(f"SUMMARY:")
    print(f"  • Files scanned:     {results['files_scanned']}")
    print(f"  • Files modified:    {results['files_modified']}")
    print(f"  • Total replacements: {results['total_replacements']}")
    print()
    
    if results["by_file"]:
        print(f"TOP MODIFIED FILES:")
        for item in sorted(results["by_file"], key=lambda x: x["replacements"], reverse=True)[:10]:
            print(f"  • {item['file']} - {item['replacements']} replacements")
    
    if results["total_replacements"] > 0:
        print(f"\nTheme now loads {results['total_replacements']} assets locally instead of CDN!")


if __name__ == "__main__":
    main()
