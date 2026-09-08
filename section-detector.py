#!/usr/bin/env python3
"""
Section Detector - Data-Driven Section Discovery (v3.7)
======================================================

THE PRINCIPLE (user's actual requirement)
-----------------------------------------
When cloning a web page to a Shopify theme, the TOOL decides which components
become sections - automatically, from what is ACTUALLY on the page. If the page
has a mega menu, slideshow, FAQ, product carousel those become sections. If
the page does NOT have them they are NOT generated. No hardcoded default
stacks, no "add this section manually." The clone mirrors reality.

HOW SHOPIFY MAKES THIS POSSIBLE
-------------------------------
Shopify renders every section wrapped in a predictable DOM marker:
  <div id="shopify-section-template--18543504588894__banner_8FyJPG" class="shopify-section">
  <div id="shopify-section-header" class="shopify-section">
  <div id="shopify-section-announcement-bar" class="shopify-section">

The section TYPE leaks in the id:
  - template sections:  shopify-section-template--<themeid>__<TYPE>_<random>
  - named sections:     shopify-section-<TYPE>
  - group sections:     shopify-section-group-<TYPE>  (header/footer groups)

We parse these markers from the captured page HTML to recover the EXACT,
ordered list of sections that exist on each page - then hand that to
json-template-builder so the JSON template references real, discovered sections.

When the source is NOT Shopify (a Lovable/React/static site), section markers
won't exist. We fall back to STRUCTURAL detection: identify recognizable
component patterns (slideshow/carousel, mega menu, FAQ/accordion, marquee,
logo bar, testimonials, newsletter, image-with-text) by DOM/class heuristics - 
and again, only emit what is present.

USAGE
-----
  # Detect sections on one page
  python3 section-detector.py <page.html>

  # Detect across a crawled clone (pages/*.html) -> writes detected-sections.json
  python3 section-detector.py --clone <clone_dir>

  # Self-test
  python3 section-detector.py --selftest

OUTPUT (detected-sections.json)
-------------------------------
  {
    "index": {
       "source": "shopify-markers" | "structural",
       "sections": [
         {"type": "banner", "id": "...", "order": 0, "evidence": "shopify-section id"},
         {"type": "product_carousel", ...},
         ...
       ]
    },
    "product": {...},
    ...
  }
"""

import os
import re
import sys
import json
from pathlib import Path

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Installing beautifulsoup4...")
    os.system(sys.executable + " -m pip install beautifulsoup4 lxml -q")
    from bs4 import BeautifulSoup, Tag


# ----------------------------------------------------------------------------
# Shopify marker parsing (authoritative when present)
# ----------------------------------------------------------------------------

# template--<digits>__<type>_<RANDOM>   the RANDOM suffix is [A-Za-z0-9]{6,}
RE_TEMPLATE_SECTION = re.compile(
    r"shopify-section-template--\d+__([a-z0-9_]+?)_[A-Za-z0-9]{5,}\b")
# named: shopify-section-<type>  (type may contain hyphens), NOT followed by template
RE_NAMED_SECTION = re.compile(r"shopify-section-(?!template--)([a-z0-9][a-z0-9\-]*)")
RE_GROUP_SECTION = re.compile(r"shopify-section-group-([a-z0-9\-]+)")

# named sections we treat as layout/group, not page-body sections
LAYOUT_SECTIONS = {"header", "footer", "announcement-bar", "mini-cart",
                   "cart-drawer", "popup", "modal"}

# non-section noise: app wrappers, Shopify internals, malformed group containers.
# These appear as shopify-section markers but are NOT buyer-customizable sections.
NOISE_TYPES = {
    "protect", "speculation_rules", "speculation-rules", "swym-wishlist-plus-custom",
    "pixel", "web-pixel", "perf", "sentry", "consent", "gdpr",
}
# regex-style noise: section-group containers like "sections--18543501017182"
NOISE_PATTERNS = [
    re.compile(r"^sections--\d+$"),
    re.compile(r"^section-group"),
    re.compile(r"^\d+$"),
]


def _is_noise(stype):
    if stype in NOISE_TYPES:
        return True
    return any(rx.match(stype) for rx in NOISE_PATTERNS)


def _normalize_type(t):
    """Strip a trailing single-char random fragment the regex may leave."""
    t = t.strip("_-")
    # collapse known multiword types so 'product_carousel_x' -> 'product_carousel'
    KNOWN = ["editorial_multiproduct_carousel", "product_carousel",
             "quick_links", "generic_text", "image_with_text",
             "collection_list", "featured_collection", "rich_text",
             "slideshow", "mega_menu", "faq", "newsletter", "banner",
             "spacer", "flexible", "testimonials", "logo_list", "video",
             "gallery", "marquee", "countdown", "blog_posts", "map",
             "contact_form", "custom_liquid"]
    for k in KNOWN:
        if t == k or t.startswith(k + "_") or t == k.replace("_", ""):
            return k
    return t


def _extract_section_inner(html, marker):
    """Extract the inner HTML of a section by balanced-tag matching on its
    wrapper element. Returns cleaned markup (scripts/styles/noise stripped) or
    None. This is what makes the clone 1:1 in CONTENT, not just structure."""
    m = re.search(r'<(section|div)\s[^>]*id="' + re.escape(marker) + r'"[^>]*>', html)
    if not m:
        return None
    tag = m.group(1)
    start = m.end()
    depth = 1
    for mm in re.finditer(r'</?' + tag + r'\b[^>]*>', html[start:]):
        if mm.group(0).startswith('</'):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            inner = html[start:start + mm.start()]
            return _clean_section_markup(inner)
    return None


def _clean_section_markup(inner):
    """Strip scripts, performance marks, stylesheet links, and Shopify runtime
    noise so the section body is lean, editor-friendly markup."""
    inner = re.sub(r'<script[\s\S]*?</script>', '', inner, flags=re.IGNORECASE)
    inner = re.sub(r'<style[\s\S]*?</style>', '', inner, flags=re.IGNORECASE)
    # drop stylesheet <link> tags (theme.css handles styling)
    inner = re.sub(r'<link\b[^>]*rel="stylesheet"[^>]*>', '', inner, flags=re.IGNORECASE)
    # drop <noscript>
    inner = re.sub(r'<noscript[\s\S]*?</noscript>', '', inner, flags=re.IGNORECASE)
    # collapse excessive blank lines
    inner = re.sub(r'\n\s*\n\s*\n+', '\n\n', inner)
    return inner.strip()


def detect_shopify_sections(html):
    """Return ordered list of section dicts from shopify-section markers, or []."""
    # find markers in DOCUMENT ORDER by scanning id="shopify-section-..."
    sections = []
    seen = set()
    order = 0
    # iterate over every id occurrence in source order
    for m in re.finditer(r'id="(shopify-section[^"]+)"', html):
        marker = m.group(1)
        tmpl = RE_TEMPLATE_SECTION.search(marker)
        grp = RE_GROUP_SECTION.search(marker)
        named = RE_NAMED_SECTION.search(marker)
        if tmpl:
            stype = _normalize_type(tmpl.group(1))
            kind = "template"
        elif grp:
            stype = _normalize_type(grp.group(1))
            kind = "group"
        elif named:
            stype = _normalize_type(named.group(1))
            kind = "named"
        else:
            continue
        if _is_noise(stype):
            continue
        key = (stype, marker)
        if key in seen:
            continue
        seen.add(key)
        is_layout = stype in LAYOUT_SECTIONS or kind == "group"
        inner = _extract_section_inner(html, marker)
        sections.append({
            "type": stype,
            "marker": marker,
            "kind": kind,
            "layout": is_layout,
            "order": order,
            "evidence": "shopify-section id (" + kind + ")",
            "has_markup": bool(inner),
            "markup_len": len(inner) if inner else 0,
            "_inner": inner,  # consumed by detect_clone, stripped before JSON
        })
        order += 1
    return sections


# ----------------------------------------------------------------------------
# Structural detection (fallback for non-Shopify sources)
# ----------------------------------------------------------------------------

# Each detector: (section_type, predicate(soup) -> matched Tag or None)
def _find(soup, selectors=None, class_kw=None, role=None):
    if selectors:
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el
    if class_kw:
        for el in soup.find_all(True):
            if not isinstance(el, Tag):
                continue
            cls = el.get("class")
            if isinstance(cls, (list, tuple)):
                cls = " ".join(str(c) for c in cls)
            else:
                cls = str(cls or "")
            idv = str(el.get("id") or "")
            hay = (cls + " " + idv).lower()
            if any(kw in hay for kw in class_kw):
                return el
    return None


STRUCTURAL_DETECTORS = [
    ("slideshow", dict(class_kw=["slideshow", "carousel", "slider", "swiper",
                                 "splide", "glide", "flickity"])),
    ("mega_menu", dict(class_kw=["mega-menu", "megamenu", "mega_menu",
                                 "nav-dropdown", "header__dropdown"])),
    ("faq", dict(class_kw=["faq", "accordion", "collapsible", "disclosure"])),
    ("marquee", dict(class_kw=["marquee", "ticker", "scrolling-text"])),
    ("logo_list", dict(class_kw=["logo-list", "logo-bar", "brands", "as-seen",
                                 "press-bar"])),
    ("testimonials", dict(class_kw=["testimonial", "review-carousel",
                                    "quotes", "social-proof"])),
    ("product_carousel", dict(class_kw=["product-carousel", "product-slider",
                                        "featured-products", "product-grid"])),
    ("collection_list", dict(class_kw=["collection-list", "collection-grid",
                                       "categories"])),
    ("image_with_text", dict(class_kw=["image-with-text", "image-text",
                                       "split-section", "feature-row"])),
    ("video", dict(selectors=["video", "iframe[src*='youtube']",
                              "iframe[src*='vimeo']"])),
    ("gallery", dict(class_kw=["gallery", "lookbook", "masonry", "instagram"])),
    ("countdown", dict(class_kw=["countdown", "timer", "deal-clock"])),
    ("newsletter", dict(class_kw=["newsletter", "email-signup", "subscribe",
                                  "klaviyo-form"])),
    ("blog_posts", dict(class_kw=["blog-posts", "article-list", "latest-posts"])),
    ("map", dict(selectors=["iframe[src*='maps.google']", "iframe[src*='/maps']"],
                 class_kw=["store-map", "google-map"])),
    ("contact_form", dict(selectors=["form[action*='/contact']"])),
    ("rich_text", dict(class_kw=["rich-text", "rte-section", "text-block"])),
]


def detect_structural_sections(html):
    soup = BeautifulSoup(html, "lxml")
    found = []
    order = 0
    for stype, kw in STRUCTURAL_DETECTORS:
        el = _find(soup, **kw)
        if el is not None:
            found.append({
                "type": stype,
                "marker": None,
                "kind": "structural",
                "layout": stype in LAYOUT_SECTIONS,
                "order": order,
                "evidence": "structural match (" + (el.name or "?") + ")",
            })
            order += 1
    return found


# ----------------------------------------------------------------------------
# Page-level detection
# ----------------------------------------------------------------------------

PAGE_STEM_TO_TYPE = {
    "homepage": "index", "home": "index", "index": "index",
    "product": "product", "collection": "collection",
    "search": "search", "cart": "cart", "404": "404",
    "page": "page", "blog": "blog", "article": "article",
    "list-collections": "list-collections",
}


def detect_page(html):
    """Return (source, sections[]).

    HARD RULE (no hallucination): if the page contains ANY shopify-section
    markers, it is a Shopify-rendered page - we trust the markers ONLY and
    NEVER fall back to structural guessing. A Shopify cart/search page
    legitimately has few or zero customizable body sections; inventing
    slideshow/faq/gallery from loose keyword matches in the footer/widgets is
    exactly the hallucination we must avoid. Structural detection runs ONLY
    when the source is genuinely non-Shopify (zero markers present)."""
    has_any_marker = bool(re.search(r'id="shopify-section', html))
    if has_any_marker:
        shopify = detect_shopify_sections(html)
        return "shopify-markers", shopify
    # genuinely non-Shopify source (Lovable / React / static HTML)
    structural = detect_structural_sections(html)
    return "structural", structural


def detect_clone(clone_dir):
    clone = Path(clone_dir)
    pages_dir = clone / "pages"
    candidates = []
    if pages_dir.exists():
        candidates = list(pages_dir.glob("*.html"))
    # also accept extracted/homepage.html
    extra = clone / "extracted" / "homepage.html"
    if extra.exists():
        candidates.append(extra)

    # directory to hold extracted section markup (1:1 content from source)
    markup_dir = clone / "detected-section-markup"
    markup_dir.mkdir(parents=True, exist_ok=True)

    result = {}
    for p in candidates:
        stem = p.stem.lower()
        ptype = PAGE_STEM_TO_TYPE.get(stem, stem)
        if ptype in result:
            continue
        html = p.read_text(encoding="utf-8", errors="replace")
        source, sections = detect_page(html)

        # persist each section's real markup to a file, strip _inner from JSON
        for s in sections:
            inner = s.pop("_inner", None)
            if inner and not s.get("layout"):
                fname = ptype + "__" + s["type"] + "_" + str(s["order"]) + ".html"
                (markup_dir / fname).write_text(inner, encoding="utf-8")
                s["markup_file"] = str(markup_dir / fname)

        result[ptype] = {
            "source": source,
            "page_file": str(p),
            "sections": sections,
            "body_sections": [s for s in sections if not s["layout"]],
            "layout_sections": [s for s in sections if s["layout"]],
        }

    out = clone / "detected-sections.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, out


SELFTEST_SHOPIFY = """<html><body>
<div id="shopify-section-announcement-bar" class="shopify-section">promo</div>
<div id="shopify-section-header" class="shopify-section">nav</div>
<div id="shopify-section-template--184__banner_8FyJPG" class="shopify-section">hero</div>
<div id="shopify-section-template--184__product_carousel_xT4nJT" class="shopify-section">carousel</div>
<div id="shopify-section-template--184__quick_links_btcrQr" class="shopify-section">links</div>
<div id="shopify-section-template--184__editorial_multiproduct_carousel_aB" class="shopify-section">editorial</div>
<div id="shopify-section-footer" class="shopify-section">footer</div>
</body></html>"""

SELFTEST_NONSHOPIFY = """<html><body>
<header><nav class="mega-menu">menu</nav></header>
<div class="hero-slideshow swiper">slides</div>
<section class="faq-accordion">questions</section>
<div class="logo-bar">brands</div>
<form action="/contact">contact</form>
<div class="newsletter-signup">subscribe</div>
</body></html>"""


def run_selftest():
    print("=== Shopify-marker source ===")
    src, secs = detect_page(SELFTEST_SHOPIFY)
    print("source:", src)
    for s in secs:
        tag = " [layout]" if s["layout"] else ""
        print("  " + str(s["order"]) + ". " + s["type"] + tag + "  <- " + s["evidence"])

    print("\n=== Non-Shopify (structural) source ===")
    src, secs = detect_page(SELFTEST_NONSHOPIFY)
    print("source:", src)
    for s in secs:
        tag = " [layout]" if s["layout"] else ""
        print("  " + str(s["order"]) + ". " + s["type"] + tag + "  <- " + s["evidence"])


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--selftest":
        run_selftest()
        return
    if args[0] == "--clone":
        if len(args) < 2:
            print("Usage: section-detector.py --clone <clone_dir>")
            return
        result, out = detect_clone(args[1])
        for ptype, info in result.items():
            body = info["body_sections"]
            print(ptype + " (" + info["source"] + "): "
                  + ", ".join(s["type"] for s in body) if body
                  else ptype + " (" + info["source"] + "): <no body sections>")
        print("\nWritten: " + str(out))
        return
    # single page
    html = Path(args[0]).read_text(encoding="utf-8", errors="replace")
    src, secs = detect_page(html)
    for s in secs:
        s.pop("_inner", None)
    print(json.dumps({"source": src, "sections": secs}, indent=2))


if __name__ == "__main__":
    main()
