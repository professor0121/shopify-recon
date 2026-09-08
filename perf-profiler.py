#!/usr/bin/env python3
"""
PERFORMANCE PROFILER - Shopify Store Performance Analysis
Analyzes: page weight, asset breakdown, script count, render-blocking, recommendations
Part of Shopify Recon | 2026-06-21

Usage: python3 perf-profiler.py <input-dir> [output-dir]
       python3 perf-profiler.py --url=https://store.com
"""

import json
import sys
import os
import re
from collections import Counter
from datetime import datetime


def analyze_page_weight(html):
    """Analyze total page weight"""
    html_size = len(html.encode('utf-8'))
    
    # Count inline CSS
    inline_css = 0
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.DOTALL):
        inline_css += len(match.group(1))
    
    # Count inline JS
    inline_js = 0
    for match in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
        if not match.group(1).strip():
            continue
        inline_js += len(match.group(1))
    
    # External resources
    external_css = re.findall(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]*)"', html, re.IGNORECASE)
    external_js = re.findall(r'<script[^>]*src="([^"]*)"[^>]*>', html, re.IGNORECASE)
    external_images = re.findall(r'<img[^>]*src="([^"]*)"', html, re.IGNORECASE)
    external_fonts = re.findall(r'@import\s+url\(["\']?([^"\')]*)["\']?\)', html)
    
    # CDN analysis
    cdn_sources = Counter()
    for url in external_css + external_js:
        if "cdn.shopify.com" in url:
            cdn_sources["Shopify CDN"] += 1
        elif "cloudfront" in url:
            cdn_sources["CloudFront"] += 1
        elif "googleapis" in url:
            cdn_sources["Google"] += 1
        elif "cloudflare" in url:
            cdn_sources["Cloudflare"] += 1
        else:
            cdn_sources["Other/First-party"] += 1
    
    return {
        "html_size": html_size,
        "html_size_kb": round(html_size / 1024, 1),
        "inline_css_size": inline_css,
        "inline_css_kb": round(inline_css / 1024, 1),
        "inline_js_size": inline_js,
        "inline_js_kb": round(inline_js / 1024, 1),
        "external_css_count": len(external_css),
        "external_js_count": len(external_js),
        "external_image_count": len(external_images),
        "external_font_count": len(external_fonts),
        "external_css_urls": external_css[:20],
        "external_js_urls": external_js[:20],
        "cdn_sources": dict(cdn_sources.most_common()),
        "estimated_total_weight_kb": round((html_size + inline_css + inline_js) / 1024, 1),
    }


def analyze_scripts(html):
    """Analyze script loading strategy"""
    scripts = {
        "total": 0,
        "async": 0,
        "defer": 0,
        "render_blocking": 0,
        "inline": 0,
        "external": 0,
        "module": 0,
    }
    
    for match in re.finditer(r'<script([^>]*)>', html, re.IGNORECASE):
        attrs = match.group(1)
        scripts["total"] += 1
        
        if "async" in attrs.lower():
            scripts["async"] += 1
        elif "defer" in attrs.lower():
            scripts["defer"] += 1
        elif "src=" in attrs:
            scripts["render_blocking"] += 1
        
        if "src=" in attrs:
            scripts["external"] += 1
        else:
            scripts["inline"] += 1
        
        if 'type="module"' in attrs.lower():
            scripts["module"] += 1
    
    return scripts


def analyze_images(html):
    """Analyze image optimization"""
    images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    
    lazy = 0
    responsive = 0
    webp = 0
    has_width = 0
    
    for img in images:
        if "loading=" in img.lower():
            lazy += 1
        if "srcset=" in img.lower() or "sizes=" in img.lower():
            responsive += 1
        if ".webp" in img.lower():
            webp += 1
        if "width=" in img.lower():
            has_width += 1
    
    return {
        "total": len(images),
        "lazy_loaded": lazy,
        "responsive": responsive,
        "webp_format": webp,
        "with_dimensions": has_width,
        "optimization_rate": round(lazy / len(images) * 100, 1) if images else 0,
    }


def analyze_fonts(html):
    """Analyze font loading strategy"""
    # Google Fonts
    google_fonts = re.findall(r'fonts\.googleapis\.com/css\?family=([^"\'&]+)', html)
    
    # Font-display
    font_display_swap = len(re.findall(r'font-display:\s*swap', html, re.IGNORECASE))
    
    # @font-face declarations
    font_face_count = len(re.findall(r'@font-face', html, re.IGNORECASE))
    
    # Preload fonts
    preload_fonts = len(re.findall(r'<link[^>]*rel="preload"[^>]*font', html, re.IGNORECASE))
    
    return {
        "google_fonts": google_fonts[:5],
        "google_fonts_count": len(google_fonts),
        "font_face_declarations": font_face_count,
        "font_display_swap_count": font_display_swap,
        "preloaded_fonts": preload_fonts,
    }


def analyze_render_blocking(html):
    """Detect render-blocking resources"""
    blocking = []
    
    # Render-blocking CSS
    for match in re.finditer(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]*)"[^>]*>', html, re.IGNORECASE):
        attrs = match.group(0)
        if "media=" not in attrs.lower() or 'media="all"' in attrs.lower():
            blocking.append({"type": "css", "url": match.group(1)[:100]})
    
    # Render-blocking JS (no async/defer)
    for match in re.finditer(r'<script\s+src="([^"]*)"[^>]*>', html, re.IGNORECASE):
        attrs = match.group(0)
        if "async" not in attrs.lower() and "defer" not in attrs.lower():
            blocking.append({"type": "js", "url": match.group(1)[:100]})
    
    return {
        "total_blocking": len(blocking),
        "css_blocking": sum(1 for b in blocking if b["type"] == "css"),
        "js_blocking": sum(1 for b in blocking if b["type"] == "js"),
        "items": blocking[:15],
    }


def compute_perf_score(data):
    """Compute performance score (0-100)"""
    score = 100
    issues = []
    recommendations = []
    
    # Page weight (max -30)
    weight_kb = data["page_weight"]["estimated_total_weight_kb"]
    if weight_kb > 500:
        score -= 30
        issues.append(f"Page weight is {weight_kb}KB (very heavy, >500KB)")
        recommendations.append("Reduce inline CSS/JS, use external minified files")
    elif weight_kb > 200:
        score -= 15
        issues.append(f"Page weight is {weight_kb}KB (heavy, >200KB)")
    elif weight_kb > 100:
        score -= 5
    
    # Render-blocking resources (max -20)
    blocking = data["render_blocking"]["total_blocking"]
    if blocking > 20:
        score -= 20
        issues.append(f"{blocking} render-blocking resources (very high)")
        recommendations.append("Add 'async' or 'defer' to non-critical scripts")
    elif blocking > 10:
        score -= 10
        issues.append(f"{blocking} render-blocking resources (high)")
    elif blocking > 5:
        score -= 5
    
    # Script loading (max -15)
    scripts = data["scripts"]
    if scripts["total"] > 50:
        score -= 15
        issues.append(f"{scripts['total']} scripts loaded (very high)")
        recommendations.append("Reduce script count, bundle where possible")
    elif scripts["total"] > 30:
        score -= 8
    
    # Image optimization (max -15)
    img = data["images"]
    if img["total"] > 0:
        if img["optimization_rate"] < 30:
            score -= 15
            issues.append(f"Only {img['optimization_rate']}% images use lazy loading")
            recommendations.append("Add 'loading=\"lazy\"' to below-fold images")
        elif img["optimization_rate"] < 60:
            score -= 8
        
        if img["webp_format"] == 0 and img["total"] > 5:
            score -= 5
            issues.append("No WebP images detected (using older formats)")
            recommendations.append("Convert images to WebP for 30-50% size reduction")
    
    # Inline CSS/JS (max -10)
    if data["page_weight"]["inline_css_kb"] > 50:
        score -= 5
        issues.append(f"Inline CSS is {data['page_weight']['inline_css_kb']}KB")
    if data["page_weight"]["inline_js_kb"] > 100:
        score -= 5
        issues.append(f"Inline JS is {data['page_weight']['inline_js_kb']}KB")
    
    # Fonts (max -10)
    fonts = data["fonts"]
    if fonts["google_fonts_count"] > 3:
        score -= 5
        issues.append(f"{fonts['google_fonts_count']} Google Fonts loaded (limit to 2)")
    if fonts["font_display_swap_count"] == 0 and fonts["font_face_declarations"] > 0:
        score -= 5
        issues.append("Missing font-display: swap (causes FOIT)")
        recommendations.append("Add 'font-display: swap' to @font-face declarations")
    
    return {
        "score": max(score, 0),
        "issues": issues,
        "recommendations": recommendations,
    }


def analyze(html, store_name="Store"):
    """Run full performance analysis"""
    data = {
        "store": store_name,
        "analyzed_at": datetime.now().isoformat(),
        "page_weight": analyze_page_weight(html),
        "scripts": analyze_scripts(html),
        "images": analyze_images(html),
        "fonts": analyze_fonts(html),
        "render_blocking": analyze_render_blocking(html),
    }
    
    data["perf_score"] = compute_perf_score(data)
    
    return data


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Profiler")
    parser.add_argument("input", nargs="?", help="Input directory with homepage.html")
    parser.add_argument("--url", help="Store URL")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-o", "--output")
    
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
        with open(html_path) as f:
            html = f.read()
        store_name = os.path.basename(args.input)
    else:
        parser.print_help()
        sys.exit(1)
    
    if not html or len(html) < 500:
        print("Could not get HTML")
        sys.exit(1)
    
    data = analyze(html, store_name)
    
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        score = data["perf_score"]["score"]
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        pw = data["page_weight"]
        sc = data["scripts"]
        im = data["images"]
        ft = data["fonts"]
        rb = data["render_blocking"]
        
        print(f"\n╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  PERFORMANCE PROFILE - {store_name[:35]:<35}║")
        print(f"╠═══════════════════════════════════════════════════════════════╣")
        print(f"║                                                                ║")
        print(f"║  Perf Score:      [{bar}] {score}%{'':<{16 - len(str(score))}}║")
        print(f"║                                                                ║")
        print(f"║   Page Weight:                                               ║")
        print(f"║     • HTML:           {pw['html_size_kb']}KB{'':<{40 - len(str(pw['html_size_kb'])) - 2}}║")
        print(f"║     • Inline CSS:     {pw['inline_css_kb']}KB{'':<{40 - len(str(pw['inline_css_kb'])) - 2}}║")
        print(f"║     • Inline JS:      {pw['inline_js_kb']}KB{'':<{40 - len(str(pw['inline_js_kb'])) - 2}}║")
        print(f"║     • Est. Total:     {pw['estimated_total_weight_kb']}KB{'':<{40 - len(str(pw['estimated_total_weight_kb'])) - 2}}║")
        print(f"║                                                                ║")
        print(f"║  Scripts:          {sc['total']} total{'':<{38 - len(str(sc['total']))}}║")
        print(f"║     • External:       {sc['external']}{'':<{40 - len(str(sc['external']))}}║")
        print(f"║     • Inline:         {sc['inline']}{'':<{40 - len(str(sc['inline']))}}║")
        print(f"║     • Async:          {sc['async']}{'':<{40 - len(str(sc['async']))}}║")
        print(f"║     • Defer:          {sc['defer']}{'':<{40 - len(str(sc['defer']))}}║")
        print(f"║     • Render-blocking:{sc['render_blocking']}{'':<{40 - len(str(sc['render_blocking']))}}║")
        print(f"║                                                                ║")
        print(f"║   Images:           {im['total']} total{'':<{38 - len(str(im['total']))}}║")
        print(f"║     • Lazy loaded:    {im['lazy_loaded']} ({im['optimization_rate']}%){'':<{30 - len(str(im['lazy_loaded'])) - len(str(im['optimization_rate']))}}║")
        print(f"║     • Responsive:     {im['responsive']}{'':<{40 - len(str(im['responsive']))}}║")
        print(f"║     • WebP:           {im['webp_format']}{'':<{40 - len(str(im['webp_format']))}}║")
        print(f"║                                                                ║")
        print(f"║  Fonts:                                                     ║")
        print(f"║     • Google Fonts:   {ft['google_fonts_count']}{'':<{40 - len(str(ft['google_fonts_count']))}}║")
        print(f"║     • @font-face:     {ft['font_face_declarations']}{'':<{40 - len(str(ft['font_face_declarations']))}}║")
        print(f"║     • font-display:   {ft['font_display_swap_count']}{'':<{40 - len(str(ft['font_display_swap_count']))}}║")
        print(f"║                                                                ║")
        print(f"║  Render-blocking:  {rb['total_blocking']} resources{'':<{30 - len(str(rb['total_blocking']))}}║")
        print(f"║     • CSS:            {rb['css_blocking']}{'':<{40 - len(str(rb['css_blocking']))}}║")
        print(f"║     • JS:             {rb['js_blocking']}{'':<{40 - len(str(rb['js_blocking']))}}║")
        print(f"║                                                                ║")
        
        if data["perf_score"]["issues"]:
            count = len(data["perf_score"]["issues"])
            print(f"║   Issues ({count}):{'':<{46 - len(str(count))}}║")
            for issue in data["perf_score"]["issues"][:5]:
                print(f"║     • {issue[:52]:<52}║")
            print(f"║                                                                ║")
        
        if data["perf_score"]["recommendations"]:
            count = len(data["perf_score"]["recommendations"])
            print(f"║  Recommendations ({count}):{'':<{42 - len(str(count))}}║")
            for rec in data["perf_score"]["recommendations"][:3]:
                print(f"║     {rec[:51]:<51}║")
            print(f"║                                                                ║")
        
        print(f"╚═══════════════════════════════════════════════════════════════╝")
    
    if args.output:
        os.makedirs(args.output, exist_ok=True)
        with open(os.path.join(args.output, "perf-analysis.json"), "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved: {args.output}/perf-analysis.json")


if __name__ == "__main__":
    main()
