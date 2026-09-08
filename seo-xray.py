#!/usr/bin/env python3
"""
SEO X-RAY - Deep SEO Analysis for Shopify Stores
Extracts: meta tags, Open Graph, Twitter Cards, JSON-LD, headings, links, images
Part of Shopify Recon | 2026-06-21

Usage: python3 seo-xray.py <input-dir> [output-dir]
       python3 seo-xray.py --url=https://store.com
"""

import json
import sys
import os
import re
from collections import Counter
from datetime import datetime


def extract_meta_tags(html):
    """Extract all meta tags"""
    metas = []
    
    # Standard meta tags
    for match in re.finditer(r'<meta\s+([^>]+?)/?>', html, re.IGNORECASE):
        attrs_str = match.group(1)
        attrs = {}
        for attr_match in re.finditer(r'(\w[\w-]*)=["\']([^"\']*)["\']', attrs_str):
            attrs[attr_match.group(1).lower()] = attr_match.group(2)
        
        if attrs:
            metas.append(attrs)
    
    return metas


def extract_open_graph(metas):
    """Extract Open Graph tags"""
    og = {}
    for meta in metas:
        prop = meta.get("property", "")
        if prop.startswith("og:"):
            og[prop[3:]] = meta.get("content", "")
        elif prop.startswith("fb:"):
            og[prop] = meta.get("content", "")
    return og


def extract_twitter_cards(metas):
    """Extract Twitter Card tags"""
    twitter = {}
    for meta in metas:
        name = meta.get("name", "")
        if name.startswith("twitter:"):
            twitter[name[8:]] = meta.get("content", "")
    return twitter


def extract_json_ld(html):
    """Extract JSON-LD structured data"""
    blocks = []
    
    for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    blocks.append(item)
            else:
                blocks.append(data)
        except json.JSONDecodeError:
            blocks.append({"_raw": raw[:500], "_error": "parse_error"})
    
    return blocks


def extract_headings(html):
    """Extract heading hierarchy"""
    headings = []
    for match in re.finditer(r'<(h[1-6])[^>]*>(.*?)</\1>', html, re.DOTALL | re.IGNORECASE):
        level = int(match.group(1)[1])
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if text:
            headings.append({"level": level, "text": text[:100]})
    return headings


def extract_links(html):
    """Extract and categorize links"""
    links = {
        "internal": [],
        "external": [],
        "products": [],
        "collections": [],
        "pages": [],
        "blogs": [],
        "social": [],
    }
    
    seen = set()
    for match in re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>', html, re.IGNORECASE):
        href = match.group(1)
        if href in seen or href.startswith("#") or href.startswith("javascript:"):
            continue
        seen.add(href)
        
        if href.startswith("/"):
            links["internal"].append(href)
            if "/products/" in href:
                links["products"].append(href)
            elif "/collections/" in href:
                links["collections"].append(href)
            elif "/pages/" in href:
                links["pages"].append(href)
            elif "/blogs/" in href:
                links["blogs"].append(href)
        elif href.startswith("http"):
            if any(social in href for social in ["facebook.com", "twitter.com", "instagram.com", 
                                                  "youtube.com", "tiktok.com", "pinterest.com", 
                                                  "linkedin.com", "snapchat.com"]):
                links["social"].append(href)
            else:
                links["external"].append(href)
    
    return links


def extract_images(html):
    """Extract image data"""
    images = []
    for match in re.finditer(r'<img[^>]*src="([^"]*)"[^>]*(?:alt="([^"]*)")?[^>]*>', html, re.IGNORECASE):
        src = match.group(1)
        alt = match.group(2) or ""
        images.append({"src": src[:200], "alt": alt, "has_alt": bool(alt)})
    
    # Also check for srcset
    srcset_count = len(re.findall(r'srcset="', html))
    
    return {
        "images": images[:50],
        "total_count": len(images),
        "with_alt": sum(1 for i in images if i["has_alt"]),
        "without_alt": sum(1 for i in images if not i["has_alt"]),
        "srcset_count": srcset_count,
    }


def extract_canonical(html):
    """Extract canonical URL"""
    match = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', html, re.IGNORECASE)
    return match.group(1) if match else None


def extract_hreflang(html):
    """Extract hreflang tags for international SEO"""
    hreflangs = []
    for match in re.finditer(r'<link[^>]*rel="alternate"[^>]*hreflang="([^"]*)"[^>]*href="([^"]*)"', html, re.IGNORECASE):
        hreflangs.append({"lang": match.group(1), "href": match.group(2)})
    return hreflangs


def extract_title_description(html):
    """Extract title and meta description"""
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else None
    
    desc = None
    for match in re.finditer(r'<meta\s+name="description"\s+content="([^"]*)"', html, re.IGNORECASE):
        desc = match.group(1)
        break
    
    return {
        "title": title,
        "title_length": len(title) if title else 0,
        "description": desc,
        "description_length": len(desc) if desc else 0,
    }


def compute_seo_score(data):
    """Compute overall SEO score (0-100)"""
    score = 0
    issues = []
    
    # Title (15 pts)
    if data["title_desc"]["title"]:
        length = data["title_desc"]["title_length"]
        if 30 <= length <= 60:
            score += 15
        elif length > 0:
            score += 8
            issues.append(f"Title length is {length} (ideal: 30-60)")
    else:
        issues.append("Missing <title> tag")
    
    # Meta description (15 pts)
    if data["title_desc"]["description"]:
        length = data["title_desc"]["description_length"]
        if 120 <= length <= 160:
            score += 15
        elif length > 0:
            score += 8
            issues.append(f"Description length is {length} (ideal: 120-160)")
    else:
        issues.append("Missing meta description")
    
    # Open Graph (10 pts)
    if data["open_graph"]:
        if "title" in data["open_graph"]:
            score += 3
        if "image" in data["open_graph"]:
            score += 4
        if "url" in data["open_graph"]:
            score += 3
    else:
        issues.append("Missing Open Graph tags")
    
    # Twitter Cards (5 pts)
    if data["twitter_cards"]:
        score += 5
    else:
        issues.append("Missing Twitter Card tags")
    
    # JSON-LD (15 pts)
    if data["json_ld"]:
        score += min(len(data["json_ld"]) * 5, 15)
    else:
        issues.append("No JSON-LD structured data found")
    
    # Headings (10 pts)
    if data["headings"]:
        h1_count = sum(1 for h in data["headings"] if h["level"] == 1)
        if h1_count == 1:
            score += 10
        elif h1_count > 1:
            score += 5
            issues.append(f"Multiple H1 tags ({h1_count}) - should be exactly 1")
        else:
            issues.append("No H1 tag found")
    else:
        issues.append("No heading tags found")
    
    # Images alt text (10 pts)
    if data["images"]["total_count"] > 0:
        alt_ratio = data["images"]["with_alt"] / data["images"]["total_count"]
        score += int(alt_ratio * 10)
        if alt_ratio < 0.5:
            issues.append(f"Only {alt_ratio*100:.0f}% of images have alt text")
    else:
        score += 10  # No images = no issue
    
    # Canonical (5 pts)
    if data["canonical"]:
        score += 5
    else:
        issues.append("Missing canonical URL")
    
    # Internal links (5 pts)
    if len(data["links"]["internal"]) > 10:
        score += 5
    elif len(data["links"]["internal"]) > 0:
        score += 3
    else:
        issues.append("Very few internal links")
    
    # Hreflang (5 pts)
    if data["hreflang"]:
        score += 5
    
    # Mobile-friendly (5 pts)
    if data["meta_tags"]:
        viewport = any(m.get("name") == "viewport" for m in data["meta_tags"])
        if viewport:
            score += 5
        else:
            issues.append("Missing viewport meta tag (not mobile-friendly)")
    
    return {"score": min(score, 100), "issues": issues}


def analyze(html, store_name="Store"):
    """Run full SEO analysis"""
    meta_tags = extract_meta_tags(html)
    
    data = {
        "store": store_name,
        "analyzed_at": datetime.now().isoformat(),
        "title_desc": extract_title_description(html),
        "meta_tags": meta_tags,
        "meta_count": len(meta_tags),
        "open_graph": extract_open_graph(meta_tags),
        "twitter_cards": extract_twitter_cards(meta_tags),
        "json_ld": extract_json_ld(html),
        "headings": extract_headings(html),
        "links": extract_links(html),
        "images": extract_images(html),
        "canonical": extract_canonical(html),
        "hreflang": extract_hreflang(html),
    }
    
    # Compute SEO score
    data["seo_score"] = compute_seo_score(data)
    
    # Summary stats
    data["stats"] = {
        "total_headings": len(data["headings"]),
        "h1_count": sum(1 for h in data["headings"] if h["level"] == 1),
        "h2_count": sum(1 for h in data["headings"] if h["level"] == 2),
        "total_links": sum(len(v) for v in data["links"].values()),
        "internal_links": len(data["links"]["internal"]),
        "external_links": len(data["links"]["external"]),
        "product_links": len(data["links"]["products"]),
        "collection_links": len(data["links"]["collections"]),
        "social_links": len(data["links"]["social"]),
        "total_images": data["images"]["total_count"],
        "images_with_alt": data["images"]["with_alt"],
        "images_without_alt": data["images"]["without_alt"],
        "json_ld_blocks": len(data["json_ld"]),
        "hreflang_count": len(data["hreflang"]),
    }
    
    return data


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="SEO X-Ray")
    parser.add_argument("input", nargs="?", help="Input directory with homepage.html")
    parser.add_argument("--url", help="Store URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-o", "--output", help="Output directory")
    
    args = parser.parse_args()
    
    html = ""
    store_name = "Unknown"
    
    if args.url:
        import subprocess
        url = args.url if args.url.startswith("http") else "https://" + args.url
        store_name = url.replace("https://", "").replace("http://", "")
        print(f"Fetching: {url}")
        result = subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "15", url],
                                capture_output=True, text=True)
        html = result.stdout
    elif args.input:
        html_path = os.path.join(args.input, "homepage.html")
        if not os.path.exists(html_path):
            print(f"No homepage.html in {args.input}")
            sys.exit(1)
        with open(html_path) as f:
            html = f.read()
        store_name = os.path.basename(args.input)
    else:
        parser.print_help()
        sys.exit(1)
    
    if not html or len(html) < 500:
        print("Could not get HTML content")
        sys.exit(1)
    
    data = analyze(html, store_name)
    
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        score = data["seo_score"]["score"]
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        
        print(f"\n╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  SEO X-RAY - {store_name[:40]:<46}║")
        print(f"╠═══════════════════════════════════════════════════════════════╣")
        print(f"║                                                                ║")
        print(f"║  SEO Score:       [{bar}] {score}%{'':<{max(0, 16 - len(str(score)))}}║")
        print(f"║                                                                ║")
        print(f"║  Title:            {str(data['title_desc']['title'])[:44]:<44}║")
        print(f"║  Title Length:     {str(data['title_desc']['title_length'])+' chars':<44}║")
        print(f"║  Description:      {str(data['title_desc']['description'] or 'Missing')[:44]:<44}║")
        print(f"║  Desc Length:      {str(data['title_desc']['description_length'])+' chars':<44}║")
        print(f"║                                                                ║")
        print(f"║   Meta Tags:       {data['meta_count']:<44}║")
        print(f"║  Open Graph:       {len(data['open_graph'])} tags{'':<{38}}║")
        print(f"║  Twitter Cards:   {len(data['twitter_cards'])} tags{'':<{38}}║")
        print(f"║  JSON-LD:          {data['stats']['json_ld_blocks']} blocks{'':<{38}}║")
        print(f"║                                                                ║")
        print(f"║  Headings:                                                  ║")
        print(f"║     • H1: {data['stats']['h1_count']:<3}  • H2: {data['stats']['h2_count']:<3}  • Total: {data['stats']['total_headings']:<3}{'':<{24}}║")
        print(f"║                                                                ║")
        print(f"║  Links:                                                     ║")
        print(f"║     • Internal:    {data['stats']['internal_links']:<5}  • External:  {data['stats']['external_links']:<5}{'':<{16}}║")
        print(f"║     • Products:    {data['stats']['product_links']:<5}  • Collections: {data['stats']['collection_links']:<5}{'':<{14}}║")
        print(f"║     • Social:      {data['stats']['social_links']:<5}{'':<{42}}║")
        print(f"║                                                                ║")
        print(f"║   Images:          {data['stats']['total_images']} total{'':<{38}}║")
        print(f"║     • With alt:     {data['stats']['images_with_alt']:<5}  • Without:   {data['stats']['images_without_alt']:<5}{'':<{16}}║")
        print(f"║                                                                ║")
        if data["canonical"]:
            print(f"║  Canonical:       {str(data['canonical'])[:44]:<44}║")
        else:
            print(f"║  Canonical:       Missing{'':<{36}}║")
        print(f"║  Hreflang:         {data['stats']['hreflang_count']} tags{'':<{38}}║")
        print(f"║                                                                ║")
        
        if data["seo_score"]["issues"]:
            print(f"║   SEO Issues ({len(data['seo_score']['issues'])}):{'':<{39}}║")
            for issue in data["seo_score"]["issues"][:5]:
                print(f"║     • {issue[:52]:<52}║")
            print(f"║                                                                ║")
        
        print(f"╚═══════════════════════════════════════════════════════════════╝")
    
    if args.output:
        os.makedirs(args.output, exist_ok=True)
        with open(os.path.join(args.output, "seo-analysis.json"), "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved: {args.output}/seo-analysis.json")


if __name__ == "__main__":
    main()
