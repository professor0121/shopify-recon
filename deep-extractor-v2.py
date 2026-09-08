#!/usr/bin/env python3
"""
DEEP CODE EXTRACTOR v2 - Advanced Web Code Extraction
Combines: BeautifulSoup parsing + webcrack deobfuscation + asset downloading
Specialized for Shopify Liquid theme reverse-engineering

Features borrowed from popular GitHub tools:
- BeautifulSoup (like Scrapy/pyquery) HTML parsing
- webcrack (2.1k) JS deobfuscation + bundle unpacking
- wget mirror mode recursive asset download
- httrack approach convert links to local
- firecrawl approach structured data extraction

Usage: python3 deep-extractor-v2.py <url> <output-dir>
Example: python3 deep-extractor-v2.py https://rothys.com ./deep-extract
"""

import json
import sys
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup


# ═══════════════════════════════════════════════════════════════════
# 1. HTML PARSER (BeautifulSoup) - Structured extraction
# ═══════════════════════════════════════════════════════════════════

class HTMLParser:
    """Parse HTML with BeautifulSoup for structured data extraction"""
    
    def __init__(self, html, base_url=""):
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, "lxml")
    
    def extract_structure(self):
        """Extract complete page structure"""
        return {
            "title": self.soup.title.string if self.soup.title else None,
            "meta_tags": self._extract_meta(),
            "headings": self._extract_headings(),
            "links": self._extract_links(),
            "images": self._extract_images(),
            "scripts": self._extract_scripts(),
            "styles": self._extract_styles(),
            "forms": self._extract_forms(),
            "sections": self._extract_shopify_sections(),
            "css_classes": self._extract_css_classes(),
            "inline_styles": self._extract_inline_styles(),
            "data_attributes": self._extract_data_attrs(),
            "json_ld": self._extract_json_ld(),
            "shopify_objects": self._extract_shopify_objects(),
        }
    
    def _extract_meta(self):
        metas = []
        for tag in self.soup.find_all("meta"):
            attrs = dict(tag.attrs)
            metas.append(attrs)
        return metas
    
    def _extract_headings(self):
        headings = []
        for level in range(1, 7):
            for h in self.soup.find_all(f"h{level}"):
                text = h.get_text(strip=True)
                if text:
                    headings.append({"level": level, "text": text[:100]})
        return headings
    
    def _extract_links(self):
        links = {"internal": [], "external": [], "product": [], "collection": [], "social": []}
        seen = set()
        
        for a in self.soup.find_all("a", href=True):
            href = a["href"]
            if href in seen or href.startswith("#"):
                continue
            seen.add(href)
            
            if href.startswith("/"):
                links["internal"].append(href)
                if "/products/" in href:
                    links["product"].append(href)
                elif "/collections/" in href:
                    links["collection"].append(href)
            elif href.startswith("http"):
                if any(s in href for s in ["facebook", "instagram", "twitter", "youtube", "tiktok"]):
                    links["social"].append(href)
                else:
                    links["external"].append(href)
        
        return links
    
    def _extract_images(self):
        images = []
        for img in self.soup.find_all("img"):
            images.append({
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
                "loading": img.get("loading", ""),
                "srcset": img.get("srcset", ""),
                "class": " ".join(img.get("class", [])),
            })
        return images
    
    def _extract_scripts(self):
        scripts = []
        for s in self.soup.find_all("script"):
            src = s.get("src", "")
            content = s.string or ""
            scripts.append({
                "src": src[:200] if src else None,
                "type": s.get("type", "text/javascript"),
                "async": s.get("async") is not None,
                "defer": s.get("defer") is not None,
                "inline_size": len(content),
                "content_preview": content[:200].strip() if content else None,
            })
        return scripts
    
    def _extract_styles(self):
        styles = []
        for link in self.soup.find_all("link", rel="stylesheet"):
            styles.append({
                "href": link.get("href", ""),
                "media": link.get("media", "all"),
            })
        for style in self.soup.find_all("style"):
            content = style.string or ""
            styles.append({
                "inline": True,
                "size": len(content),
                "content_preview": content[:200].strip() if content else None,
            })
        return styles
    
    def _extract_forms(self):
        forms = []
        for form in self.soup.find_all("form"):
            inputs = []
            for inp in form.find_all(["input", "select", "textarea"]):
                inputs.append({
                    "name": inp.get("name", ""),
                    "type": inp.get("type", inp.name),
                    "required": inp.get("required") is not None,
                })
            forms.append({
                "action": form.get("action", ""),
                "method": form.get("method", "get"),
                "inputs": inputs,
            })
        return forms
    
    def _extract_shopify_sections(self):
        """Extract Shopify section wrappers"""
        sections = []
        for el in self.soup.find_all(id=re.compile(r"shopify-section-")):
            section_id = el.get("id", "")
            classes = " ".join(el.get("class", []))
            
            # Extract section type from ID
            type_match = re.search(r'__(\w+?)_[A-Za-z0-9]+$', section_id) or re.search(r'shopify-section-(\w+)$', section_id)
            section_type = type_match.group(1) if type_match else "unknown"
            
            # Get inner HTML size
            inner = str(el)
            
            sections.append({
                "id": section_id,
                "type": section_type,
                "classes": classes,
                "html_size": len(inner),
                "has_products": "/products/" in inner,
                "has_images": "<img" in inner,
                "has_forms": "<form" in inner,
            })
        return sections
    
    def _extract_css_classes(self):
        """Extract all CSS classes used"""
        classes = Counter()
        for el in self.soup.find_all(class_=True):
            for cls in el.get("class", []):
                classes[cls] += 1
        return classes.most_common(50)
    
    def _extract_inline_styles(self):
        """Extract elements with inline styles"""
        styled = []
        for el in self.soup.find_all(style=True):
            style = el.get("style", "")
            if len(style) > 20:  # Only substantial styles
                styled.append({
                    "tag": el.name,
                    "class": " ".join(el.get("class", [])),
                    "style": style[:300],
                })
        return styled[:50]
    
    def _extract_data_attrs(self):
        """Extract all data-* attributes"""
        data_attrs = defaultdict(Counter)
        for el in self.soup.find_all(True):
            for attr, value in el.attrs.items():
                if attr.startswith("data-"):
                    data_attrs[attr][str(value)[:50]] += 1
        
        return {k: v.most_common(10) for k, v in data_attrs.items() if k.startswith("data-")}
    
    def _extract_json_ld(self):
        """Extract JSON-LD structured data"""
        blocks = []
        for s in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "{}")
                blocks.append(data)
            except:
                blocks.append({"_raw": (s.string or "")[:200]})
        return blocks
    
    def _extract_shopify_objects(self):
        """Extract Shopify JS objects (Shopify.theme, Shopify.shop, etc.)"""
        objects = {}
        
        # Find all Shopify.* assignments
        for match in re.finditer(r'(?:window\.)?Shopify\.(\w+)\s*=\s*(\{[^}]+\})', self.html):
            key = match.group(1)
            try:
                objects[key] = json.loads(match.group(2).replace("'", '"'))
            except:
                objects[key] = match.group(2)[:200]
        
        # Find Shopify.routes
        routes_match = re.search(r'Shopify\.routes\s*=\s*(\{[^}]+\})', self.html)
        if routes_match:
            try:
                objects["routes"] = json.loads(routes_match.group(1).replace("'", '"'))
            except:
                objects["routes"] = routes_match.group(1)[:200]
        
        # Find Shopify.currency
        currency_match = re.search(r'Shopify\.currency\s*=\s*(\{[^}]+\})', self.html)
        if currency_match:
            objects["currency"] = currency_match.group(1)[:200]
        
        # Find window.ShopifyAnalytics
        analytics_match = re.search(r'window\.ShopifyAnalytics(?:\.meta)?\s*=\s*(\{.*?\});', self.html, re.DOTALL)
        if analytics_match:
            objects["analytics"] = analytics_match.group(1)[:500]
        
        return objects


# ═══════════════════════════════════════════════════════════════════
# 2. JS DEOBFUSCATOR - webcrack integration
# ═══════════════════════════════════════════════════════════════════

def deobfuscate_js(js_content, output_dir, label="script"):
    """Run webcrack on JS content"""
    if not js_content or len(js_content) < 100:
        return None
    
    # Write to temp file
    tmp_file = os.path.join(output_dir, f"{label}_raw.js")
    with open(tmp_file, "w") as f:
        f.write(js_content)
    
    # Run webcrack
    result = subprocess.run(
        ["webcrack", "-o", os.path.join(output_dir, label), "-f", tmp_file],
        capture_output=True, text=True, timeout=30
    )
    
    # Read deobfuscated output
    output_file = os.path.join(output_dir, label, "deobfuscated.js")
    if os.path.exists(output_file):
        with open(output_file) as f:
            return f.read()
    
    # webcrack might output to stdout
    if result.stdout:
        return result.stdout
    
    return None


def extract_and_deobfuscate_scripts(html, output_dir):
    """Extract inline JS scripts and deobfuscate them"""
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script")
    
    deobfuscated_dir = os.path.join(output_dir, "deobfuscated-js")
    os.makedirs(deobfuscated_dir, exist_ok=True)
    
    results = []
    
    for i, script in enumerate(scripts):
        content = script.string or ""
        src = script.get("src", "")
        
        # Skip empty scripts and external scripts
        if not content or len(content) < 200:
            continue
        
        # Skip analytics/tracking
        if any(x in content[:500].lower() for x in ['gtag', 'fbq', 'datalayer', 'newrelic', 'googleanalytics']):
            continue
        
        label = f"inline_{i}"
        
        # Check if it looks minified/obfuscated
        is_minified = len(content) / content.count('\n') > 200 if content.count('\n') > 0 else True
        
        if is_minified:
            print(f"  Deobfuscating script {i} ({len(content)} bytes)...")
            deobfuscated = deobfuscate_js(content, deobfuscated_dir, label)
            
            if deobfuscated:
                results.append({
                    "script_index": i,
                    "original_size": len(content),
                    "deobfuscated_size": len(deobfuscated),
                    "is_minified": True,
                    "deobfuscated_preview": deobfuscated[:500],
                    "file": f"deobfuscated-js/{label}/deobfuscated.js",
                })
            else:
                # Save raw if webcrack fails
                raw_path = os.path.join(deobfuscated_dir, f"{label}_raw.js")
                with open(raw_path, "w") as f:
                    f.write(content)
                results.append({
                    "script_index": i,
                    "original_size": len(content),
                    "is_minified": True,
                    "file": f"deobfuscated-js/{label}_raw.js",
                })
        else:
            # Already readable, just save
            raw_path = os.path.join(deobfuscated_dir, f"{label}.js")
            with open(raw_path, "w") as f:
                f.write(content)
            results.append({
                "script_index": i,
                "original_size": len(content),
                "is_minified": False,
                "file": f"deobfuscated-js/{label}.js",
            })
    
    return results


# ═══════════════════════════════════════════════════════════════════
# 3. ASSET MIRROR - Download all CSS/JS/assets (httrack approach)
# ═══════════════════════════════════════════════════════════════════

def mirror_assets(html, base_url, output_dir, max_assets=50):
    """Download all CSS/JS/image assets, like httrack mirror mode"""
    soup = BeautifulSoup(html, "lxml")
    
    assets_dir = os.path.join(output_dir, "mirrored-assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    url_mapping = {}
    downloaded = []
    failed = []
    
    # Collect all asset URLs
    asset_urls = []
    
    # CSS
    for link in soup.find_all("link", rel="stylesheet", href=True):
        asset_urls.append(("css", link["href"]))
    
    # JS
    for script in soup.find_all("script", src=True):
        asset_urls.append(("js", script["src"]))
    
    # Images
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if not src.startswith("data:"):
            asset_urls.append(("img", src))
    
    # Download each
    for i, (asset_type, url) in enumerate(asset_urls[:max_assets]):
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and not url.startswith("//"):
            url = urljoin(base_url, url)
        elif not url.startswith("http"):
            continue
        
        # Generate filename
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or f"asset_{i}"
        filename = re.sub(r'[^\w.\-]', '_', filename)[:80]
        
        type_dir = os.path.join(assets_dir, asset_type)
        os.makedirs(type_dir, exist_ok=True)
        filepath = os.path.join(type_dir, filename)
        
        print(f"   [{i+1}/{min(len(asset_urls), max_assets)}] {filename[:40]}...", end=" ")
        
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "10",
                 "-o", filepath, url],
                capture_output=True, timeout=15
            )
            
            if os.path.exists(filepath) and os.path.getsize(filepath) > 50:
                size = os.path.getsize(filepath)
                print(f"{size//1024}KB")
                
                local_path = os.path.relpath(filepath, output_dir)
                url_mapping[url] = local_path
                downloaded.append({
                    "type": asset_type,
                    "url": url,
                    "file": local_path,
                    "size": size,
                })
            else:
                print("")
                failed.append(url)
        except:
            print("")
            failed.append(url)
        
        time.sleep(0.1)
    
    return {
        "downloaded": downloaded,
        "failed": failed,
        "url_mapping": url_mapping,
    }


# ═══════════════════════════════════════════════════════════════════
# 4. SHOPIFY-SPECIFIC EXTRACTOR - Liquid pattern detection
# ═══════════════════════════════════════════════════════════════════

def extract_liquid_patterns(html):
    """Detect Liquid template patterns in rendered HTML"""
    patterns = {
        "product_loops": [],
        "collection_loops": [],
        "cart_forms": [],
        "variant_selectors": [],
        "money_filters": [],
        "image_filters": [],
        "link_filters": [],
        "conditional_blocks": [],
    }
    
    # Product card patterns (repeated product links with images)
    product_cards = re.findall(r'<(?:div|article|li)[^>]*(?:class="[^"]*product[^"]*")[^>]*>.*?</(?:div|article|li)>', html, re.DOTALL | re.IGNORECASE)
    patterns["product_loops"] = len(product_cards)
    
    # Collection grid patterns
    collection_grids = re.findall(r'class="[^"]*(?:grid|product-grid|collection-grid)[^"]*"', html, re.IGNORECASE)
    patterns["collection_loops"] = len(collection_grids)
    
    # Cart forms
    cart_forms = re.findall(r'action="[^"]*cart/add[^"]*"', html, re.IGNORECASE)
    patterns["cart_forms"] = len(cart_forms)
    
    # Variant selectors
    variant_selects = re.findall(r'name="(?:id|variant)"', html, re.IGNORECASE)
    patterns["variant_selectors"] = len(variant_selects)
    
    # Money formatting ($ signs near prices)
    money_patterns = re.findall(r'\$[\d,.]+', html)
    patterns["money_filters"] = len(money_patterns)
    
    # Image URL patterns (Shopify CDN)
    shopify_imgs = re.findall(r'cdn\.shopify\.com/s/files/[^"\s]+', html)
    patterns["image_filters"] = len(shopify_imgs)
    
    # Internal links (Liquid link_to patterns)
    internal_links = re.findall(r'href="/(?:products|collections|pages|blogs)/[^"]+"', html)
    patterns["link_filters"] = len(internal_links)
    
    # Conditional blocks (if/unless patterns in data attributes)
    conditionals = re.findall(r'data-(?:if|unless|case|when)="[^"]+"', html, re.IGNORECASE)
    patterns["conditional_blocks"] = len(conditionals)
    
    return patterns


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("DEEP CODE EXTRACTOR v2")
        print("━" * 69)
        print()
        print("Usage: python3 deep-extractor-v2.py <url> <output-dir>")
        print("Example: python3 deep-extractor-v2.py https://rothys.com ./deep")
        sys.exit(1)
    
    url = sys.argv[1]
    if not url.startswith("http"):
        url = "https://" + url
    
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)
    
    store_name = urlparse(url).netloc
    
    print("DEEP CODE EXTRACTOR v2")
    print("━" * 69)
    print(f"  Store: {store_name}")
    print(f"  Output: {output_dir}")
    print()
    
    # Step 1: Fetch HTML
    print("  [1/5] Fetching HTML...")
    result = subprocess.run(
        ["curl", "-s", "-L", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
         "--max-time", "20", url],
        capture_output=True, text=True
    )
    html = result.stdout
    print(f"    {len(html)} bytes")
    
    # Save raw HTML
    with open(os.path.join(output_dir, "homepage.html"), "w") as f:
        f.write(html)
    
    # Step 2: Parse HTML structure
    print("\n  [2/5] Parsing HTML structure (BeautifulSoup)...")
    parser = HTMLParser(html, url)
    structure = parser.extract_structure()
    print(f"    {len(structure['sections'])} sections, {len(structure['scripts'])} scripts, {len(structure['images'])} images")
    
    # Save structure
    with open(os.path.join(output_dir, "structure.json"), "w") as f:
        json.dump(structure, f, indent=2, default=str)
    
    # Step 3: Deobfuscate JS
    print("\n  [3/5] Deobfuscating JavaScript (webcrack)...")
    deobfuscated = extract_and_deobfuscate_scripts(html, output_dir)
    print(f"    {len(deobfuscated)} scripts processed")
    
    with open(os.path.join(output_dir, "deobfuscated-scripts.json"), "w") as f:
        json.dump(deobfuscated, f, indent=2, default=str)
    
    # Step 4: Mirror assets
    print(f"\n  [4/5] Mirroring assets (CSS/JS/images)...")
    mirrored = mirror_assets(html, url, output_dir, max_assets=30)
    print(f"    {len(mirrored['downloaded'])} downloaded, {len(mirrored['failed'])} failed")
    
    with open(os.path.join(output_dir, "asset-mapping.json"), "w") as f:
        json.dump(mirrored, f, indent=2, default=str)
    
    # Step 5: Extract Liquid patterns
    print("\n  [5/5] Detecting Shopify Liquid patterns...")
    liquid_patterns = extract_liquid_patterns(html)
    print(f"    Product cards: {liquid_patterns['product_loops']}")
    print(f"    Cart forms: {liquid_patterns['cart_forms']}")
    print(f"    Money patterns: {liquid_patterns['money_filters']}")
    print(f"    Shopify CDN images: {liquid_patterns['image_filters']}")
    
    with open(os.path.join(output_dir, "liquid-patterns.json"), "w") as f:
        json.dump(liquid_patterns, f, indent=2)
    
    # Summary
    print(f"\nDEEP EXTRACTION COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print()
    print(f"EXTRACTION SUMMARY:")
    print(f"  • HTML size:          {len(html):,} bytes")
    print(f"  • Shopify sections:   {len(structure['sections'])}")
    print(f"  • Scripts:            {len(structure['scripts'])}")
    print(f"  • Images:             {len(structure['images'])}")
    print(f"  • CSS classes:        {len(structure['css_classes'])}")
    print(f"  • Forms:              {len(structure['forms'])}")
    print(f"  • JSON-LD blocks:     {len(structure['json_ld'])}")
    print(f"  • Shopify objects:    {len(structure['shopify_objects'])}")
    print(f"  • Deobfuscated JS:    {len(deobfuscated)} scripts")
    print(f"  • Mirrored assets:    {len(mirrored['downloaded'])}")
    print(f"  • Liquid patterns:    {sum(liquid_patterns.values())}")
    print()
    print(f"FILES GENERATED:")
    print(f"  • homepage.html - Raw HTML")
    print(f"  • structure.json - Parsed HTML structure")
    print(f"  • deobfuscated-scripts.json - Deobfuscated JS info")
    print(f"  • asset-mapping.json - URL local file mapping")
    print(f"  • liquid-patterns.json - Detected Liquid patterns")
    print(f"  • mirrored-assets/ - Downloaded CSS/JS/images")
    print(f"  • deobfuscated-js/ - Deobfuscated JS files")


if __name__ == "__main__":
    main()
