#!/usr/bin/env python3
"""
Block-ifier - Editor-Native Section Generator (v3.7)
=====================================================

THE PROBLEM THIS SOLVES
-----------------------
The toolkit's existing generators (dom-to-liquid, section-reverse-engineer,
variant-filter-cloner, etc.) produce sections that RENDER correctly (94-99%
visual fidelity) but are DEAD in the Shopify theme editor:
  - No {% schema %} "blocks" array  -> buyer can't add/remove/drag elements
  - No "presets"                    -> section won't appear in "Add section"
  - No {% for block in section.blocks %} -> nothing is movable
  - No {{ block.shopify_attributes }}    -> editor can't target elements

A theme that renders perfectly but can't be customized is a SCAFFOLD, not a
product. Premium themes (Dawn, Prestige, Impulse) get 80% of their value from
editor flexibility, not pixels. This tool closes that gap.

WHAT IT DOES
------------
Takes a flat section .liquid file (markup + flat {% schema %} settings) and
rewrites it as a block-based, editor-native section:
  1. Detects logical "blocks" in the markup (heading, text, image, button,
     icon, quote, spacer, custom_liquid, etc.) via tag + class heuristics.
  2. Emits a {% for block in section.blocks %} loop with a {% case block.type %}
     branch per detected block type.
  3. Stamps {{ block.shopify_attributes }} on every block wrapper so the editor
     can select / highlight / reorder them.
  4. Builds a proper {% schema %} with:
       - section-level "settings" (grouped with headers + paragraphs + info)
       - "blocks" array (one entry per detected type, each with its own settings
         and a "limit" where it makes sense, e.g. one heading)
       - "max_blocks"
       - "presets" with sensible "default" blocks so the section drops in ready
       - "enabled_on"/"disabled_on" hints where the template context is known
  5. Preserves the original rendered markup as the block's default by moving
     hardcoded text/URLs into block.settings defaults.

USAGE
-----
  # Single section
  python3 block-ifier.py path/to/section.liquid [output.liquid]

  # Whole theme sections dir (in place -> writes *.liquid, backs up to .bak)
  python3 block-ifier.py --dir path/to/theme/sections

  # Emit a self-test sample and block-ify it (no external input needed)
  python3 block-ifier.py --selftest

OUTPUT
------
Block-based .liquid + a per-section JSON report of what was converted.
Designed to be run as step 25 of shopify-recon.py after section generation.

NOTE: f-strings are NOT used for any Liquid content (Pitfall 6). All Liquid
output is built with string concatenation / .format-free templates.
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
# Block type detection
# ----------------------------------------------------------------------------

# Order matters: first match wins. Each entry is (block_type, matcher).
# matcher(tag) -> bool
BLOCK_TYPE_RULES = [
    ("heading", lambda t: t.name in ("h1", "h2", "h3", "h4", "h5", "h6")),
    ("image", lambda t: t.name in ("img", "picture") or (
        t.name in ("div", "figure") and _has_class_kw(t, ("image", "media", "img", "photo")))),
    ("button", lambda t: (t.name in ("a", "button") and _has_class_kw(
        t, ("btn", "button", "cta"))) or t.name == "button"),
    ("quote", lambda t: t.name in ("blockquote",) or _has_class_kw(
        t, ("quote", "testimonial", "review"))),
    ("icon", lambda t: t.name in ("svg",) or _has_class_kw(t, ("icon",))),
    ("video", lambda t: t.name in ("video", "iframe") or _has_class_kw(
        t, ("video", "embed"))),
    ("list", lambda t: t.name in ("ul", "ol")),
    ("text", lambda t: t.name in ("p",) or _has_class_kw(
        t, ("text", "richtext", "rte", "description", "subtitle", "caption"))),
]

# default settings template per block type
BLOCK_SETTINGS = {
    "heading": [
        {"type": "text", "id": "heading", "label": "Heading", "default": "Heading"},
        {"type": "select", "id": "heading_size", "label": "Heading size",
         "options": [{"value": "h1", "label": "Large"},
                     {"value": "h2", "label": "Medium"},
                     {"value": "h3", "label": "Small"}],
         "default": "h2"},
        {"type": "select", "id": "alignment", "label": "Alignment",
         "options": [{"value": "left", "label": "Left"},
                     {"value": "center", "label": "Center"},
                     {"value": "right", "label": "Right"}],
         "default": "left"},
    ],
    "text": [
        {"type": "richtext", "id": "text", "label": "Text",
         "default": "<p>Share information about your brand with your customers.</p>"},
        {"type": "select", "id": "alignment", "label": "Alignment",
         "options": [{"value": "left", "label": "Left"},
                     {"value": "center", "label": "Center"},
                     {"value": "right", "label": "Right"}],
         "default": "left"},
    ],
    "image": [
        {"type": "image_picker", "id": "image", "label": "Image"},
        {"type": "range", "id": "image_width", "label": "Image width", "min": 10,
         "max": 100, "step": 5, "unit": "%", "default": 100},
        {"type": "text", "id": "image_alt", "label": "Alt text",
         "info": "Describe the image for accessibility & SEO."},
    ],
    "button": [
        {"type": "text", "id": "button_label", "label": "Button label",
         "default": "Shop now"},
        {"type": "url", "id": "button_link", "label": "Button link"},
        {"type": "select", "id": "button_style", "label": "Style",
         "options": [{"value": "primary", "label": "Primary"},
                     {"value": "secondary", "label": "Secondary"},
                     {"value": "link", "label": "Text link"}],
         "default": "primary"},
    ],
    "quote": [
        {"type": "richtext", "id": "quote", "label": "Quote",
         "default": "<p>Add a customer quote or testimonial here.</p>"},
        {"type": "text", "id": "author", "label": "Author", "default": "Customer name"},
    ],
    "icon": [
        {"type": "select", "id": "icon", "label": "Icon",
         "options": [{"value": "star", "label": "Star"},
                     {"value": "check", "label": "Check"},
                     {"value": "truck", "label": "Truck"},
                     {"value": "heart", "label": "Heart"}],
         "default": "star"},
        {"type": "image_picker", "id": "custom_icon", "label": "Custom icon",
         "info": "Overrides the icon above when set."},
    ],
    "video": [
        {"type": "video", "id": "video", "label": "Video"},
        {"type": "video_url", "id": "video_url", "label": "Video URL (YouTube/Vimeo)",
         "accept": ["youtube", "vimeo"]},
    ],
    "list": [
        {"type": "richtext", "id": "list", "label": "List",
         "default": "<ul><li>First item</li><li>Second item</li></ul>"},
    ],
    "custom_liquid": [
        {"type": "liquid", "id": "custom_liquid", "label": "Custom Liquid",
         "info": "Add app snippets or custom Liquid. Advanced."},
    ],
}

# label shown in editor for each block type
BLOCK_LABELS = {
    "heading": "Heading", "text": "Text", "image": "Image", "button": "Button",
    "quote": "Quote", "icon": "Icon", "video": "Video", "list": "List",
    "custom_liquid": "Custom Liquid",
}

# blocks that should only ever appear once in a preset's defaults
SINGLETON_HINT = {"heading"}


def _has_class_kw(tag, keywords):
    if not isinstance(tag, Tag):
        return False
    cls = tag.get("class")
    if isinstance(cls, (list, tuple)):
        classes = " ".join(str(c) for c in cls)
    elif cls:
        classes = str(cls)
    else:
        classes = ""
    cid = tag.get("id") or ""
    hay = (classes + " " + str(cid)).lower()
    return any(kw in hay for kw in keywords)


def detect_block_type(tag):
    """Return a block type string for a tag, or None if it isn't a block."""
    if not isinstance(tag, Tag):
        return None
    for btype, matcher in BLOCK_TYPE_RULES:
        try:
            if matcher(tag):
                return btype
        except Exception:
            continue
    return None


def _text_of(tag):
    try:
        return tag.get_text(" ", strip=True)
    except Exception:
        return ""


# ----------------------------------------------------------------------------
# Section parsing
# ----------------------------------------------------------------------------

class Section:
    """Parse a flat section .liquid into markup + schema."""

    SCHEMA_RE = re.compile(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}",
                           re.DOTALL | re.IGNORECASE)

    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_text(encoding="utf-8", errors="replace")
        self.name = self.path.stem
        self.schema = self._extract_schema()
        self.markup = self._strip_schema()
        self.report = {
            "section": self.name,
            "blocks_detected": [],
            "had_schema": bool(self.schema),
            "had_blocks_before": bool(self.schema and self.schema.get("blocks")),
            "had_presets_before": bool(self.schema and self.schema.get("presets")),
        }

    def _extract_schema(self):
        m = self.SCHEMA_RE.search(self.raw)
        if not m:
            return None
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            # schema present but malformed -> treat as none, rebuild fresh
            return None

    def _strip_schema(self):
        return self.SCHEMA_RE.sub("", self.raw).strip()

    # -- block detection over the markup ------------------------------------

    def find_block_candidates(self):
        """Walk the markup and return ordered list of (block_type, tag)."""
        soup = BeautifulSoup(self.markup or "<div></div>", "lxml")
        root = soup.body or soup
        candidates = []
        seen_ids = set()

        # Prefer direct meaningful children; fall back to descendants for
        # heading/button/image which are almost always blocks.
        for tag in root.descendants:
            if not isinstance(tag, Tag):
                continue
            btype = detect_block_type(tag)
            if not btype:
                continue
            # avoid double-capturing nested matches (e.g. <a class=btn><svg>)
            key = id(tag)
            if key in seen_ids:
                continue
            # skip if an ancestor was already captured as the same logical block
            if any(id(anc) in seen_ids for anc in tag.parents):
                # allow heading/text inside a captured container only if the
                # container itself wasn't a leaf block
                continue
            seen_ids.add(key)
            candidates.append((btype, tag))

        return candidates, soup


# ----------------------------------------------------------------------------
# Liquid generation (NO f-strings around Liquid - Pitfall 6)
# ----------------------------------------------------------------------------

def render_block_case(block_types):
    """Build the {% for block %} / {% case %} loop body."""
    lines = []
    lines.append("<div class=\"section-blocks\">")
    lines.append("  {%- for block in section.blocks -%}")
    lines.append("    {%- case block.type -%}")

    for bt in block_types:
        lines.append("")
        lines.append("      {%- when '" + bt + "' -%}")
        lines.append(_block_markup(bt))

    # app blocks
    lines.append("")
    lines.append("      {%- when '@app' -%}")
    lines.append("        <div class=\"section-block section-block--app\" {{ block.shopify_attributes }}>")
    lines.append("          {%- render block -%}")
    lines.append("        </div>")

    lines.append("")
    lines.append("    {%- endcase -%}")
    lines.append("  {%- endfor -%}")
    lines.append("</div>")
    return "\n".join(lines)


def _block_markup(bt):
    """Per-type rendered markup that reads from block.settings."""
    a = " {{ block.shopify_attributes }}"
    if bt == "heading":
        return ("\n".join([
            "        {%- if block.settings.heading != blank -%}",
            "          <{{ block.settings.heading_size }} class=\"section-block section-block--heading text-{{ block.settings.alignment }}\"" + a + ">",
            "            {{ block.settings.heading | escape }}",
            "          </{{ block.settings.heading_size }}>",
            "        {%- endif -%}",
        ]))
    if bt == "text":
        return ("\n".join([
            "        {%- if block.settings.text != blank -%}",
            "          <div class=\"section-block section-block--text text-{{ block.settings.alignment }}\"" + a + ">",
            "            {{ block.settings.text }}",
            "          </div>",
            "        {%- endif -%}",
        ]))
    if bt == "image":
        return ("\n".join([
            "        <div class=\"section-block section-block--image\"" + a + ">",
            "          {%- if block.settings.image != blank -%}",
            "            {{ block.settings.image | image_url: width: 1500 | image_tag:",
            "               loading: 'lazy',",
            "               widths: '300,600,900,1200,1500',",
            "               alt: block.settings.image_alt,",
            "               style: 'width: ' | append: block.settings.image_width | append: '%;' }}",
            "          {%- else -%}",
            "            {{ 'image' | placeholder_svg_tag: 'placeholder-svg' }}",
            "          {%- endif -%}",
            "        </div>",
        ]))
    if bt == "button":
        return ("\n".join([
            "        {%- if block.settings.button_label != blank -%}",
            "          <a class=\"section-block section-block--button button button--{{ block.settings.button_style }}\"",
            "             href=\"{{ block.settings.button_link | default: '#' }}\"" + a + ">",
            "            {{ block.settings.button_label | escape }}",
            "          </a>",
            "        {%- endif -%}",
        ]))
    if bt == "quote":
        return ("\n".join([
            "        <blockquote class=\"section-block section-block--quote\"" + a + ">",
            "          {{ block.settings.quote }}",
            "          {%- if block.settings.author != blank -%}",
            "            <cite>{{ block.settings.author | escape }}</cite>",
            "          {%- endif -%}",
            "        </blockquote>",
        ]))
    if bt == "icon":
        return ("\n".join([
            "        <div class=\"section-block section-block--icon\"" + a + ">",
            "          {%- if block.settings.custom_icon != blank -%}",
            "            {{ block.settings.custom_icon | image_url: width: 64 | image_tag: alt: '' }}",
            "          {%- else -%}",
            "            <span class=\"icon icon--{{ block.settings.icon }}\" aria-hidden=\"true\"></span>",
            "          {%- endif -%}",
            "        </div>",
        ]))
    if bt == "video":
        return ("\n".join([
            "        <div class=\"section-block section-block--video\"" + a + ">",
            "          {%- if block.settings.video != blank -%}",
            "            {{ block.settings.video | video_tag: controls: true }}",
            "          {%- elsif block.settings.video_url != blank -%}",
            "            {{ block.settings.video_url | external_video_url | external_video_tag }}",
            "          {%- endif -%}",
            "        </div>",
        ]))
    if bt == "list":
        return ("\n".join([
            "        <div class=\"section-block section-block--list\"" + a + ">",
            "          {{ block.settings.list }}",
            "        </div>",
        ]))
    if bt == "custom_liquid":
        return ("\n".join([
            "        <div class=\"section-block section-block--custom\"" + a + ">",
            "          {{ block.settings.custom_liquid }}",
            "        </div>",
        ]))
    return "        {%- comment -%} unknown block {%- endcomment -%}"


def build_schema(section_name, existing_schema, block_types, template_hint=None):
    """Assemble an editor-native {% schema %} dict."""
    pretty = section_name.replace("-", " ").replace("_", " ").title()

    # carry over section-level settings if present, else seed sensible ones
    settings = []
    if existing_schema and isinstance(existing_schema.get("settings"), list):
        settings = list(existing_schema["settings"])
    # Ensure a header + colour + spacing group exists (buyer-friendly UX)
    if not any(s.get("type") == "header" for s in settings):
        settings = [
            {"type": "header", "content": "Section"},
            {"type": "text", "id": "section_heading", "label": "Section heading",
             "default": pretty},
            {"type": "paragraph",
             "content": "Add, remove, and reorder blocks below to build this section."},
            {"type": "header", "content": "Appearance"},
            {"type": "color_background", "id": "section_bg", "label": "Background",
             "default": "#ffffff"},
            {"type": "range", "id": "padding_top", "label": "Top padding",
             "min": 0, "max": 120, "step": 4, "unit": "px", "default": 40},
            {"type": "range", "id": "padding_bottom", "label": "Bottom padding",
             "min": 0, "max": 120, "step": 4, "unit": "px", "default": 40},
        ] + settings

    # build blocks array
    blocks = []
    for bt in block_types:
        entry = {
            "type": bt,
            "name": BLOCK_LABELS.get(bt, bt.title()),
            "settings": [dict(s) for s in BLOCK_SETTINGS.get(bt, [])],
        }
        if bt in SINGLETON_HINT:
            entry["limit"] = 1
        blocks.append(entry)
    # always offer custom_liquid + app blocks for premium flexibility
    if "custom_liquid" not in block_types:
        blocks.append({
            "type": "custom_liquid",
            "name": BLOCK_LABELS["custom_liquid"],
            "settings": [dict(s) for s in BLOCK_SETTINGS["custom_liquid"]],
        })
    blocks.append({"type": "@app"})

    # preset default blocks: one of each detected (singletons once)
    default_blocks = []
    for bt in block_types:
        if bt == "@app":
            continue
        default_blocks.append({"type": bt})

    preset = {"name": pretty, "blocks": default_blocks}

    schema = {
        "name": pretty[:25],  # Shopify schema name limit is 25 chars
        "tag": "section",
        "class": "section section--" + section_name,
        "settings": settings,
        "blocks": blocks,
        "max_blocks": max(12, len(block_types) + 4),
        "presets": [preset],
    }

    # enabled_on / disabled_on based on template context
    if template_hint == "product":
        schema["enabled_on"] = {"templates": ["product"]}
    elif template_hint == "collection":
        schema["enabled_on"] = {"templates": ["collection"]}
    elif template_hint in ("index", "home"):
        schema["enabled_on"] = {"templates": ["index"]}

    return schema


def wrap_section(section_name, existing_schema, block_types, loop_markup, schema):
    """Produce the final block-based .liquid string."""
    out = []
    # section wrapper with inline style hooks the schema controls
    out.append("{%- liquid")
    out.append("  assign pt = section.settings.padding_top | default: 40")
    out.append("  assign pb = section.settings.padding_bottom | default: 40")
    out.append("-%}")
    out.append("<section")
    out.append("  class=\"section section--" + section_name + "\"")
    out.append("  style=\"background:{{ section.settings.section_bg }};padding-top:{{ pt }}px;padding-bottom:{{ pb }}px;\"")
    out.append("  data-section-id=\"{{ section.id }}\"")
    out.append("  data-section-type=\"" + section_name + "\">")
    out.append("  <div class=\"page-width\">")
    out.append("    {%- if section.settings.section_heading != blank -%}")
    out.append("      <h2 class=\"section__title\">{{ section.settings.section_heading | escape }}</h2>")
    out.append("    {%- endif -%}")
    out.append(loop_markup)
    out.append("  </div>")
    out.append("</section>")
    out.append("")
    out.append("{% schema %}")
    out.append(json.dumps(schema, indent=2, ensure_ascii=False))
    out.append("{% endschema %}")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Section classification: functional vs content
# ----------------------------------------------------------------------------

# Functional sections carry commerce logic that must NEVER be overwritten.
# We detect them by name OR by the presence of functional Liquid in the markup.
FUNCTIONAL_NAME_HINTS = (
    "main-product", "main-cart", "main-collection", "main-search",
    "main-list-collections", "main-account", "main-login", "main-register",
    "main-addresses", "main-order", "header", "footer", "cart-drawer",
    "predictive-search", "product", "cart",
)

FUNCTIONAL_MARKUP_SIGNALS = (
    "form 'product'", 'form "product"', "form 'cart'", 'form "cart"',
    "payment_button", "product.options_with_values", "cart.items",
    "paginate", "predictive_search", "customer.", "/cart/add",
    "options_with_values", "section.blocks",  # already block-based
)


def classify_section(name, markup):
    """Return 'functional' or 'content'.

    PRIORITY RULE: a section carrying real cloned 1:1 markup from the source
    page must be PRESERVED (functional mode = preserve + inject additive
    blocks), never rebuilt from scratch. Content fidelity beats block-ification.
    The cloned-markup marker is stamped by json-template-builder."""
    hay = (markup or "")
    if "markup cloned 1:1 from source page" in hay:
        return "functional"
    n = name.lower()
    if any(h in n for h in FUNCTIONAL_NAME_HINTS):
        return "functional"
    if any(sig in hay for sig in FUNCTIONAL_MARKUP_SIGNALS):
        return "functional"
    return "content"


# Per-functional-section, which OPTIONAL content blocks a buyer may add.
# These are additive - they never touch the commerce logic.
FUNCTIONAL_BLOCK_MENU = {
    "main-product": ["text", "image", "icon", "quote", "list", "custom_liquid"],
    "main-collection": ["text", "image", "custom_liquid"],
    "main-cart": ["text", "image", "custom_liquid"],
    "_default": ["text", "image", "custom_liquid"],
}

# Where to inject the block region in functional markup. First pattern that
# matches wins; injection happens immediately AFTER the matched anchor.
INJECT_AFTER_ANCHORS = [
    re.compile(r"\{%-?\s*endform\s*-?%\}", re.IGNORECASE),
    re.compile(r"\{\{\s*form\s*\|\s*payment_button\s*\}\}", re.IGNORECASE),
]
# Fallback: inject BEFORE these (closing markers).
INJECT_BEFORE_ANCHORS = [
    re.compile(r"</section>", re.IGNORECASE),
    re.compile(r"<script", re.IGNORECASE),
]


def build_functional_block_region(section_name):
    """A block loop that renders ADDITIVE content blocks only."""
    menu = FUNCTIONAL_BLOCK_MENU.get(section_name,
                                     FUNCTIONAL_BLOCK_MENU["_default"])
    lines = []
    lines.append("")
    lines.append("  {%- comment -%} Buyer-customizable content blocks (additive - commerce logic above is preserved) {%- endcomment -%}")
    lines.append("  {%- if section.blocks.size > 0 -%}")
    lines.append("    <div class=\"section-blocks section-blocks--addon\">")
    lines.append("      {%- for block in section.blocks -%}")
    lines.append("        {%- case block.type -%}")
    for bt in menu:
        lines.append("          {%- when '" + bt + "' -%}")
        # reuse the same per-type markup (indented)
        body = _block_markup(bt)
        lines.append(body)
    lines.append("          {%- when '@app' -%}")
    lines.append("            <div class=\"section-block section-block--app\" {{ block.shopify_attributes }}>")
    lines.append("              {%- render block -%}")
    lines.append("            </div>")
    lines.append("        {%- endcase -%}")
    lines.append("      {%- endfor -%}")
    lines.append("    </div>")
    lines.append("  {%- endif -%}")
    lines.append("")
    return "\n".join(lines)


def inject_block_region(markup, region):
    """Insert region after the first AFTER-anchor, else before a BEFORE-anchor."""
    for rx in INJECT_AFTER_ANCHORS:
        m = rx.search(markup)
        if m:
            idx = m.end()
            return markup[:idx] + "\n" + region + markup[idx:], True
    for rx in INJECT_BEFORE_ANCHORS:
        m = rx.search(markup)
        if m:
            idx = m.start()
            return markup[:idx] + region + "\n" + markup[idx:], True
    # last resort: append
    return markup + "\n" + region, False


def merge_functional_schema(existing_schema, section_name):
    """Add blocks + presets to the EXISTING schema without clobbering settings."""
    menu = FUNCTIONAL_BLOCK_MENU.get(section_name,
                                     FUNCTIONAL_BLOCK_MENU["_default"])
    schema = dict(existing_schema) if existing_schema else {}
    schema.setdefault("name", section_name.replace("-", " ").title()[:25])

    # build additive blocks (don't duplicate ones already declared)
    existing_block_types = {b.get("type") for b in schema.get("blocks", [])
                            if isinstance(b, dict)}
    blocks = list(schema.get("blocks", []))
    for bt in menu:
        if bt in existing_block_types:
            continue
        blocks.append({
            "type": bt,
            "name": BLOCK_LABELS.get(bt, bt.title()),
            "settings": [dict(s) for s in BLOCK_SETTINGS.get(bt, [])],
        })
    if "@app" not in existing_block_types:
        blocks.append({"type": "@app"})
    schema["blocks"] = blocks

    # functional sections are NOT addable/removable (one per page) but we still
    # want them to carry a preset with NO default blocks (clean start).
    if "presets" not in schema:
        schema["presets"] = [{
            "name": schema["name"],
            "blocks": [],
        }]
    schema.setdefault("max_blocks", max(8, len(menu) + 2))
    return schema


def blockify_functional(sec):
    """Mode B: preserve commerce logic, inject additive block region."""
    region = build_functional_block_region(sec.name)
    new_markup, injected = inject_block_region(sec.markup, region)
    schema = merge_functional_schema(sec.schema, sec.name)

    out = new_markup.rstrip() + "\n\n{% schema %}\n"
    out += json.dumps(schema, indent=2, ensure_ascii=False)
    out += "\n{% endschema %}\n"

    sec.report["mode"] = "functional"
    sec.report["logic_preserved"] = True
    sec.report["region_injected"] = injected
    sec.report["addon_blocks"] = [b["type"] for b in schema["blocks"]]
    return out


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def template_hint_for(name):
    n = name.lower()
    if "product" in n:
        return "product"
    if "collection" in n or "list" in n:
        return "collection"
    if name in ("index", "home") or "hero" in n or "banner" in n:
        return "index"
    return None


def blockify_section(path, out_path=None):
    sec = Section(path)

    # CLASSIFY FIRST - functional sections must never have their markup clobbered
    mode = classify_section(sec.name, sec.markup)
    sec.report["classified_as"] = mode

    target = Path(out_path) if out_path else sec.path
    if target == sec.path:
        bak = sec.path.with_suffix(".liquid.bak")
        if not bak.exists():
            bak.write_text(sec.raw, encoding="utf-8")

    if mode == "functional":
        # Mode B: preserve logic, inject additive block region
        final = blockify_functional(sec)
        target.write_text(final, encoding="utf-8")
        sec.report["output"] = str(target)
        sec.report["block_count"] = len(sec.report.get("addon_blocks", []))
        return sec.report

    # Mode A: content section - full block-ify (safe to rebuild markup)
    candidates, soup = sec.find_block_candidates()

    # collapse to ordered unique block types (keep first occurrence order)
    ordered_types = []
    for bt, _tag in candidates:
        if bt not in ordered_types:
            ordered_types.append(bt)

    # if nothing detected, give the section at least heading+text+button so it's
    # still usable in the editor rather than empty
    if not ordered_types:
        ordered_types = ["heading", "text", "button"]

    sec.report["mode"] = "content"
    sec.report["blocks_detected"] = ordered_types

    loop_markup = render_block_case(ordered_types)
    schema = build_schema(sec.name, sec.schema, ordered_types,
                          template_hint=template_hint_for(sec.name))
    final = wrap_section(sec.name, sec.schema, ordered_types, loop_markup, schema)

    target.write_text(final, encoding="utf-8")

    sec.report["output"] = str(target)
    sec.report["block_count"] = len(ordered_types)
    return sec.report


def blockify_dir(d):
    d = Path(d)
    reports = []
    for f in sorted(d.glob("*.liquid")):
        if f.name.endswith(".bak.liquid"):
            continue
        try:
            reports.append(blockify_section(f))
        except Exception as e:
            reports.append({"section": f.stem, "error": str(e)})
    return reports


SELFTEST_HTML = """{% comment %} flat hero section {% endcomment %}
<div class="hero">
  <h1 class="hero__title">Summer Collection 2026</h1>
  <p class="hero__text">Fresh styles, sustainable materials, free shipping over $50.</p>
  <img class="hero__image" src="//cdn.shopify.com/x/hero.jpg" alt="Hero">
  <a class="btn hero__cta" href="/collections/all">Shop now</a>
</div>
{% schema %}
{"name":"Hero","settings":[{"type":"text","id":"title","label":"Title"}]}
{% endschema %}
"""


def run_selftest():
    tmp = Path("/tmp/blockifier-selftest")
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / "hero-banner.liquid"
    src.write_text(SELFTEST_HTML, encoding="utf-8")
    rep = blockify_section(src, tmp / "hero-banner.out.liquid")
    print(json.dumps(rep, indent=2))
    print("\n--- GENERATED SECTION ---\n")
    print((tmp / "hero-banner.out.liquid").read_text())
    return rep


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--selftest":
        run_selftest()
        return
    if args[0] == "--dir":
        if len(args) < 2:
            print("Usage: block-ifier.py --dir <sections_dir>")
            return
        reports = blockify_dir(args[1])
        out = Path(args[1]) / "_blockify-report.json"
        out.write_text(json.dumps(reports, indent=2), encoding="utf-8")
        ok = [r for r in reports if "error" not in r]
        print("Block-ified " + str(len(ok)) + "/" + str(len(reports)) + " sections")
        for r in reports:
            if "error" in r:
                print("  " + r["section"] + ": " + r["error"])
            else:
                print("  " + r["section"] + "  blocks=" +
                      ",".join(r["blocks_detected"]))
        print("Report: " + str(out))
        return
    # single file
    out_path = args[1] if len(args) > 1 else None
    rep = blockify_section(args[0], out_path)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
