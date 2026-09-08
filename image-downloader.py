#!/usr/bin/env python3
"""
IMAGE DOWNLOADER - Download All Images from Shopify Store
Downloads product images, collection images, assets local files
Replaces CDN URLs with local references in theme
Part of Shopify Recon | 2026-06-21

Usage: python3 image-downloader.py <extracted-dir> [output-dir]
Example: python3 image-downloader.py ./rothys-extract ./assets/images
"""

import json
import sys
import os
import re
import subprocess
import time
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse, unquote


def extract_all_image_urls(html, products_data=None):
    """Extract all unique image URLs from HTML + product data"""
    urls = set()
    
    # From HTML img tags
    for match in re.finditer(r'<img[^>]*src="([^"]+)"', html, re.IGNORECASE):
        url = match.group(1)
        if should_download(url):
            urls.add(normalize_url(url))
    
    # From srcset
    for match in re.finditer(r'srcset="([^"]+)"', html, re.IGNORECASE):
        srcset = match.group(1)
        for src in srcset.split(","):
            url = src.strip().split(" ")[0]
            if should_download(url):
                urls.add(normalize_url(url))
    
    # From CSS background-image
    for match in re.finditer(r'background(?:-image)?\s*:\s*url\(["\']?([^"\')]+)', html, re.IGNORECASE):
        url = match.group(1)
        if should_download(url):
            urls.add(normalize_url(url))
    
    # From <link> rel=icon / apple-touch-icon
    for match in re.finditer(r'<link[^>]*href="([^"]+)"[^>]*rel="[^"]*(?:icon|apple-touch)[^"]*"', html, re.IGNORECASE):
        urls.add(normalize_url(match.group(1)))
    
    # From product data
    if products_data:
        products = products_data.get("products", products_data) if isinstance(products_data, dict) else products_data
        for product in products:
            for image in product.get("images", []):
                url = image.get("src", "")
                if url:
                    urls.add(url)
            for variant in product.get("variants", []):
                featured = variant.get("featured_image")
                if featured and featured.get("src"):
                    urls.add(featured["src"])
    
    # From og:image meta
    for match in re.finditer(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.IGNORECASE):
        urls.add(normalize_url(match.group(1)))
    
    return list(urls)


def should_download(url):
    """Check if URL should be downloaded (skip data URIs, SVG placeholders, etc)"""
    if not url or len(url) < 10:
        return False
    if url.startswith("data:"):
        return False
    if url.startswith("javascript:"):
        return False
    if "placeholder" in url.lower():
        return False
    if url.endswith(".svg") and "cdn.shopify.com" not in url:
        return False
    return True


def normalize_url(url):
    """Normalize URL - add protocol if missing"""
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        url = "https:" + url if url.startswith("/") else "https://" + url
    return url


def categorize_url(url):
    """Categorize image by URL pattern"""
    url_lower = url.lower()
    
    if "cdn.shopify.com" in url_lower:
        if "/files/" in url_lower:
            return "content"  # Uploaded content images
        elif "/products/" in url_lower:
            return "products"  # Product images
        elif "/collections/" in url_lower:
            return "collections"
        elif "/shopify_assets/" in url_lower:
            return "shopify_assets"
        else:
            return "shopify_cdn"
    
    if any(ext in url_lower for ext in [".css", ".js"]):
        return "assets"
    
    if "logo" in url_lower:
        return "logo"
    
    if "favicon" in url_lower or "icon" in url_lower:
        return "favicon"
    
    if "banner" in url_lower or "hero" in url_lower:
        return "banners"
    
    return "other"


def get_filename_from_url(url, index=0):
    """Generate a clean filename from URL"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # Get the last part of the path
    filename = os.path.basename(path)
    
    # Remove query string
    filename = filename.split("?")[0]
    
    # If no extension, add .jpg
    if "." not in filename:
        filename = f"image_{index}.jpg"
    
    # Clean up
    filename = re.sub(r'[^\w.\-]', '_', filename)
    
    # Truncate if too long
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext
    
    return filename


def download_image(url, filepath, timeout=10):
    """Download a single image"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", 
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             "--max-time", str(timeout),
             "-o", filepath, url],
            capture_output=True
        )
        
        # Check if file was created and is not empty
        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            return True
        return False
    except Exception as e:
        return False


def download_all_images(urls, output_dir, max_downloads=100):
    """Download all images, organized by category"""
    
    # Create category directories
    categories = ["products", "collections", "content", "banners", "logo", 
                  "favicon", "assets", "shopify_cdn", "other"]
    for cat in categories:
        os.makedirs(os.path.join(output_dir, cat), exist_ok=True)
    
    results = {
        "downloaded": [],
        "failed": [],
        "skipped": [],
        "by_category": Counter(),
    }
    
    # Deduplicate by filename
    seen_filenames = set()
    download_count = 0
    
    for i, url in enumerate(urls):
        if download_count >= max_downloads:
            print(f"  ⏹ Reached max downloads ({max_downloads})")
            break
        
        category = categorize_url(url)
        filename = get_filename_from_url(url, i)
        
        # Handle duplicate filenames
        if filename in seen_filenames:
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{i}{ext}"
        seen_filenames.add(filename)
        
        filepath = os.path.join(output_dir, category, filename)
        
        # Skip if already exists
        if os.path.exists(filepath):
            results["skipped"].append({"url": url, "file": filepath})
            results["by_category"][category] += 1
            continue
        
        print(f"   [{download_count+1}/{min(len(urls), max_downloads)}] {filename[:50]}...", end=" ")
        
        if download_image(url, filepath):
            size = os.path.getsize(filepath)
            print(f"{size//1024}KB")
            results["downloaded"].append({
                "url": url,
                "file": filepath,
                "category": category,
                "size": size,
            })
            results["by_category"][category] += 1
            download_count += 1
        else:
            print("")
            results["failed"].append({"url": url, "file": filepath})
        
        # Rate limit
        time.sleep(0.2)
    
    return results


def generate_url_mapping(results, output_dir):
    """Generate a mapping file: original URL local path"""
    mapping = {}
    
    for item in results["downloaded"]:
        # Get relative path
        rel_path = os.path.relpath(item["file"], output_dir)
        mapping[item["url"]] = rel_path
    
    mapping_path = os.path.join(output_dir, "url-mapping.json")
    with open(mapping_path, "w") as f:
        json.dump(mapping, f, indent=2)
    
    return mapping


def generate_image_report(results, output_dir, total_urls):
    """Generate image download report"""
    
    report_path = os.path.join(output_dir, "IMAGE-REPORT.md")
    
    total_downloaded = len(results["downloaded"])
    total_failed = len(results["failed"])
    total_size = sum(r["size"] for r in results["downloaded"])
    
    with open(report_path, "w") as f:
        f.write(f"""# Image Download Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Summary

| Metric | Value |
|--------|-------|
| Total URLs Found | {total_urls} |
| Downloaded | {total_downloaded} |
| Failed | {total_failed} |
| Skipped (exists) | {len(results['skipped'])} |
| Total Size | {total_size // (1024*1024)} MB ({total_size // 1024} KB) |

---

## Images by Category

| Category | Count |
|----------|-------|
""")
        for cat, count in results["by_category"].most_common():
            f.write(f"| {cat} | {count} |\n")
        
        f.write(f"""
---

## Downloaded Files

""")
        for item in results["downloaded"][:50]:
            rel = os.path.relpath(item["file"], output_dir)
            f.write(f"- `{rel}` ({item['size']//1024}KB) - [{item['category']}]\n")
        
        if len(results["downloaded"]) > 50:
            f.write(f"\n... and {len(results['downloaded']) - 50} more\n")
        
        if results["failed"]:
            f.write(f"\n---\n\n## Failed Downloads\n\n")
            for item in results["failed"][:20]:
                f.write(f"- {item['url'][:100]}\n")
    
    return report_path


def main():
    if len(sys.argv) < 2:
        print("IMAGE DOWNLOADER")
        print("━" * 69)
        print()
        print("Usage: python3 image-downloader.py <extracted-dir> [output-dir] [--max=100]")
        print("Example: python3 image-downloader.py ./rothys-extract ./assets/images")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "images")
    
    max_downloads = 100
    for arg in sys.argv[3:]:
        if arg.startswith("--max="):
            max_downloads = int(arg.split("=")[1])
    
    print("IMAGE DOWNLOADER")
    print("━" * 69)
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Max: {max_downloads} images")
    print()
    
    # Load HTML
    html_path = os.path.join(input_dir, "homepage.html")
    if not os.path.exists(html_path):
        print(f"No homepage.html in {input_dir}")
        sys.exit(1)
    
    with open(html_path) as f:
        html = f.read()
    
    # Load product data
    products_data = None
    products_path = os.path.join(input_dir, "api", "products.json")
    if os.path.exists(products_path):
        with open(products_path) as f:
            products_data = json.load(f)
    
    # Extract URLs
    print("  [1/3] Extracting image URLs...")
    urls = extract_all_image_urls(html, products_data)
    print(f"    Found {len(urls)} unique image URLs")
    
    # Categorize
    cat_counts = Counter(categorize_url(u) for u in urls)
    print(f"\n  By category:")
    for cat, count in cat_counts.most_common():
        print(f"     • {cat}: {count}")
    
    # Download
    print(f"\n  [2/3] Downloading images (max {max_downloads})...")
    os.makedirs(output_dir, exist_ok=True)
    results = download_all_images(urls, output_dir, max_downloads)
    
    # Generate mapping + report
    print(f"\n  [3/3] Generating URL mapping + report...")
    mapping = generate_url_mapping(results, output_dir)
    report_path = generate_image_report(results, output_dir, len(urls))
    
    # Summary
    total_downloaded = len(results["downloaded"])
    total_size = sum(r["size"] for r in results["downloaded"])
    
    print(f"\nIMAGE DOWNLOAD COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  IMAGE-REPORT.md - Download report")
    print(f"  url-mapping.json - URL local path mapping")
    print()
    print(f"SUMMARY:")
    print(f"  • URLs found:      {len(urls)}")
    print(f"  • Downloaded:      {total_downloaded}")
    print(f"  • Failed:          {len(results['failed'])}")
    print(f"  • Total size:      {total_size // (1024*1024)} MB ({total_size // 1024} KB)")
    print()
    print(f"BY CATEGORY:")
    for cat, count in results["by_category"].most_common():
        print(f"  • {cat}: {count}")
    print()
    print(f"Use url-mapping.json to replace CDN URLs with local paths in theme")


if __name__ == "__main__":
    main()
