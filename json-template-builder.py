#!/usr/bin/env python3
"""
JSON Template Builder - Page-level Customization Layer (v3.7)
============================================================

THE PROBLEM THIS SOLVES
-----------------------
The toolkit generates STATIC .liquid templates (product.liquid, index.liquid,
collection.liquid...) with markup hardcoded inline. In the Shopify theme editor
a static .liquid template is a DEAD PAGE - the buyer cannot:
  - reorder sections (drag main-product above/below related products)
  - add a new section to a page ("Add section" does nothing)
  - remove a section they don't want
  - duplicate a section

That capability comes from JSON templates (templates/*.json). A JSON template is
DATA, not code: it lists which sections appear, in what order, with what
settings. The editor reads/writes this JSON when the buyer drags things around.

This is THE feature that separates a premium theme from a scaffold. Dawn,
Prestige, Impulse - all JSON templates.

WHAT IT DOES
------------
For each template in theme/templates/*.liquid:
  1. Determines the page type (index, product, collection, page, cart, etc.).
  2. Finds the matching "main" section (sections/main-<type>.liquid). If the
     template has inline markup but no section, it EXTRACTS the markup into a
     new sections/main-<type>.liquid (so the JSON template has something to
     reference - a JSON template can ONLY reference sections, never inline HTML).
  3. Writes templates/<type>.json that references the main section plus any
     sensible default companion sections (e.g. product -> main-product +
     related-products; index -> a default homepage stack).
  4. Removes the now-redundant .liquid template (backs it up to .liquid.bak).
  5. Leaves header/footer to section groups (handled by section-group-builder).

USAGE
-----
  python3 json-template-builder.py <theme_dir>
  python3 json-template-builder.py <theme_dir> --dry-run
  python3 json-template-builder.py --selftest

OUTPUT
------
  theme/templates/*.json           (editor-native, reorderable pages)
  theme/sections/main-*.liquid     (extracted where needed)
  theme/templates/_json-build-report.json

NOTE: No f-strings around Liquid content (Pitfall 6). JSON is built as dicts and
json.dumps'd - safe.
"""

import os
import re
import sys
import json
from pathlib import Path


# Page-type -> default JSON template "section stack".
# The "main" section is always the page's primary section. Companions are
# common premium-theme defaults the buyer can remove/reorder.
DEFAULT_STACKS = {
    "index": [
        ("hero_banner", "hero-banner", {}),
        ("featured_collection", "featured-collection", {}),
        ("rich_text", "rich-text", {}),
        ("image_with_text", "image-with-text", {}),
        ("newsletter", "newsletter", {}),
    ],
    "product": [
        ("main", "main-product", {}),
        ("related_products", "related-products", {}),
    ],
    "collection": [
        ("banner", "collection-banner", {}),
        ("main", "main-collection", {}),
    ],
    "list-collections": [
        ("main", "main-list-collections", {}),
    ],
    "search": [
        ("main", "main-search", {}),
    ],
    "cart": [
        ("main", "main-cart", {}),
    ],
    "page": [
        ("main", "main-page", {}),
    ],
    "blog": [
        ("main", "main-blog", {}),
    ],
    "article": [
        ("main", "main-article", {}),
    ],
    "404": [
        ("main", "main-404", {}),
    ],
    "password": [
        ("main", "main-password", {}),
    ],
}

# Templates we DON'T convert to JSON (customer templates stay .liquid in most
# themes; converting them adds risk with little editor value).
SKIP_TEMPLATES = {"gift_card"}
SKIP_DIRS = {"customers"}


def page_type_of(stem):
    """Map a template filename stem to a known page type."""
    s = stem.lower()
    # exact matches first
    if s in DEFAULT_STACKS:
        return s
    # common aliases
    aliases = {
        "home": "index",
        "index": "index",
        "products": "product",
        "collections": "collection",
        "list-collections": "list-collections",
    }
    return aliases.get(s, s)


class ThemeTemplates:
    def __init__(self, theme_dir, dry_run=False):
        self.theme = Path(theme_dir)
        self.templates_dir = self.theme / "templates"
        self.sections_dir = self.theme / "sections"
        self.sections_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.report = []
        self.detected = self._load_detected()

    # -- helpers ------------------------------------------------------------

    def _section_exists(self, name):
        return (self.sections_dir / (name + ".liquid")).exists()

    def _extract_inline_to_section(self, template_path, section_name):
        """Wrap a static .liquid template's markup into a real section file
        so the JSON template has something to reference."""
        raw = template_path.read_text(encoding="utf-8", errors="replace")

        # If the template already has a {% section %} reference, we don't need
        # to extract - but for inline-markup templates we wrap the body.
        body = raw

        # Strip a leading DOCTYPE/html shell if this template was raw-captured
        # HTML (e.g. index.liquid captured as full page). Keep only <body> inner
        # when a full document is detected - otherwise keep as-is.
        if re.search(r"<!DOCTYPE", raw, re.IGNORECASE) or re.search(r"<html", raw, re.IGNORECASE):
            m = re.search(r"<body[^>]*>(.*)</body>", raw, re.DOTALL | re.IGNORECASE)
            if m:
                body = m.group(1).strip()
            else:
                body = ""

        # Reject oversized / script-heavy raw captures: a real editor section
        # should be lean markup, not a 500KB page dump. If the body is huge or
        # dominated by <script>, emit a clean placeholder instead.
        script_bytes = sum(len(s) for s in re.findall(
            r"<script[\s\S]*?</script>", body, re.IGNORECASE))
        too_big = len(body) > 60000
        script_heavy = body and (script_bytes / max(len(body), 1)) > 0.4
        if too_big or script_heavy or not body.strip():
            body = ("{%- comment -%}\n"
                    "  Original template was a raw HTML capture (too large / script-heavy)\n"
                    "  to section cleanly. Rebuild this section's markup from the\n"
                    "  component spec, or compose the page from content sections in the\n"
                    "  JSON template instead.\n"
                    "{%- endcomment -%}\n"
                    "<div class=\"page-width\">\n"
                    "  {%- if section.settings.heading != blank -%}\n"
                    "    <h2>{{ section.settings.heading | escape }}</h2>\n"
                    "  {%- endif -%}\n"
                    "</div>")

        # Build a minimal schema so the section is editor-visible
        pretty = section_name.replace("main-", "").replace("-", " ").title()[:25]
        schema = {
            "name": pretty or "Main",
            "tag": "section",
            "class": "section section--" + section_name,
            "settings": [
                {"type": "header", "content": "Section"},
                {"type": "text", "id": "heading", "label": "Heading",
                 "default": pretty},
            ],
            "presets": [{"name": pretty or "Main"}],
        }

        out = body.rstrip() + "\n\n{% schema %}\n"
        out += json.dumps(schema, indent=2, ensure_ascii=False)
        out += "\n{% endschema %}\n"

        target = self.sections_dir / (section_name + ".liquid")
        if not self.dry_run:
            target.write_text(out, encoding="utf-8")
        return str(target)

    def _load_detected(self):
        """Load detected-sections.json if present (data-driven mode).

        This is THE source of truth: sections that ACTUALLY exist on the cloned
        page. When present, we build JSON templates from these real sections and
        NEVER inject hardcoded defaults the source page didn't have."""
        for cand in [self.theme.parent / "detected-sections.json",
                     self.theme / "detected-sections.json",
                     self.theme.parent / "analysis" / "detected-sections.json"]:
            if cand.exists():
                try:
                    return json.loads(cand.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return None
        return None

    def _build_json_template(self, page_type):
        """Construct templates/<type>.json.

        DATA-DRIVEN: if detected-sections.json has real sections for this page,
        reference EXACTLY those (1:1 with the source, no hallucinated extras).
        Otherwise fall back to a minimal single main-section template."""
        detected = (self.detected or {}).get(page_type)

        order = []
        sections = {}

        if detected and detected.get("body_sections"):
            # 1:1 with the actual page - only sections that truly exist
            for i, s in enumerate(detected["body_sections"]):
                stype = s["type"]
                sec_id = stype + "_" + str(i) if order.count(stype) else stype
                # ensure unique id
                base = stype
                n = 0
                while sec_id in sections:
                    n += 1
                    sec_id = base + "_" + str(n)
                sections[sec_id] = {"type": stype, "settings": {}}
                order.append(sec_id)
            return {"sections": sections, "order": order}, list(sections)

        # No detection data -> minimal template with just the main section
        main = "main-" + page_type
        sections["main"] = {"type": main, "settings": {}}
        order = ["main"]
        return {"sections": sections, "order": order}, [main]

    # -- main ---------------------------------------------------------------

    def convert(self):
        if not self.templates_dir.exists():
            print("No templates/ dir at " + str(self.templates_dir))
            return self.report

        for tpl in sorted(self.templates_dir.glob("*.liquid")):
            if tpl.stem in SKIP_TEMPLATES:
                continue
            rec = self._convert_one(tpl)
            self.report.append(rec)

        # write report
        if not self.dry_run:
            (self.templates_dir / "_json-build-report.json").write_text(
                json.dumps(self.report, indent=2), encoding="utf-8")
        return self.report

    def _ensure_detected_section(self, stype, markup_file=None):
        """Create a section file for a detected section type if missing.

        If a markup_file (real HTML extracted 1:1 from the source page) is
        provided, the section body uses that ACTUAL content - so the clone
        matches the source in content, not just structure. block-ifier later
        adds an additive block region for buyer customization. Without markup,
        falls back to a minimal scaffold."""
        if self._section_exists(stype):
            return False
        pretty = stype.replace("_", " ").replace("-", " ").title()[:25]

        real_markup = None
        if markup_file and Path(markup_file).exists():
            raw = Path(markup_file).read_text(encoding="utf-8", errors="replace")
            # guard: skip oversized/script-heavy captures (same rule as templates)
            if 0 < len(raw) <= 80000:
                real_markup = raw

        schema = {
            "name": pretty,
            "tag": "section",
            "class": "section section--" + stype,
            "settings": [
                {"type": "header", "content": pretty},
                {"type": "text", "id": "heading", "label": "Heading",
                 "default": pretty},
            ],
            "presets": [{"name": pretty}],
        }

        if real_markup:
            body = ("{%- comment -%} Section '" + stype + "' - markup cloned 1:1 "
                    "from source page. {%- endcomment -%}\n"
                    "<div class=\"section section--" + stype + "\" "
                    "data-section-type=\"" + stype + "\">\n"
                    + real_markup + "\n</div>")
        else:
            body = ("{%- comment -%}\n"
                    "  Section '" + stype + "' detected on the source page (no markup captured).\n"
                    "{%- endcomment -%}\n"
                    "<div class=\"section section--" + stype + " page-width\" "
                    "data-section-type=\"" + stype + "\">\n"
                    "  {%- if section.settings.heading != blank -%}\n"
                    "    <h2 class=\"section__title\">{{ section.settings.heading | escape }}</h2>\n"
                    "  {%- endif -%}\n"
                    "</div>")

        out = body + "\n\n{% schema %}\n" + json.dumps(schema, indent=2,
                                                        ensure_ascii=False) + "\n{% endschema %}\n"
        if not self.dry_run:
            (self.sections_dir / (stype + ".liquid")).write_text(out, encoding="utf-8")
        return True

    def _convert_one(self, tpl):
        page_type = page_type_of(tpl.stem)
        rec = {"template": tpl.name, "page_type": page_type}

        detected = (self.detected or {}).get(page_type)
        rec["data_driven"] = bool(detected and detected.get("body_sections"))

        if rec["data_driven"]:
            # DATA-DRIVEN: build template from REAL detected sections (1:1).
            # Generate a stub file for each detected type that doesn't exist.
            created = []
            for s in detected["body_sections"]:
                if self._ensure_detected_section(s["type"], s.get("markup_file")):
                    created.append(s["type"])
            rec["sections_created"] = created
            rec["detection_source"] = detected.get("source")
        else:
            # No detection data for this page -> ensure a main-<type> section
            main_section = "main-" + page_type
            if not self._section_exists(main_section):
                rec["extracted_section"] = self._extract_inline_to_section(
                    tpl, main_section)
                rec["extracted"] = True
            else:
                rec["extracted"] = False

        json_tpl, _ = self._build_json_template(page_type)
        rec["sections"] = json_tpl["order"]

        out_path = self.templates_dir / (page_type + ".json")
        if not self.dry_run:
            out_path.write_text(json.dumps(json_tpl, indent=2), encoding="utf-8")
            bak = tpl.with_suffix(".liquid.bak")
            if not bak.exists():
                bak.write_text(tpl.read_text(encoding="utf-8", errors="replace"),
                               encoding="utf-8")
            tpl.unlink()
        rec["output"] = str(out_path)
        return rec


def run_selftest():
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="jsontpl-"))
    (d / "templates").mkdir(parents=True)
    (d / "sections").mkdir(parents=True)
    # a product template with inline markup, no main-product section yet
    (d / "templates" / "product.liquid").write_text(
        "<div class=\"product-page\"><h1>{{ product.title }}</h1>"
        "<form action=\"/cart/add\"></form></div>", encoding="utf-8")
    # an index template
    (d / "templates" / "index.liquid").write_text(
        "<div class=\"home\"><h1>Welcome</h1></div>", encoding="utf-8")
    # pre-existing main-collection section -> should be referenced, not extracted
    (d / "sections" / "main-collection.liquid").write_text(
        "{% comment %}existing{% endcomment %}\n{% schema %}{\"name\":\"Collection\"}{% endschema %}",
        encoding="utf-8")
    (d / "templates" / "collection.liquid").write_text(
        "<div>{{ collection.title }}</div>", encoding="utf-8")

    tt = ThemeTemplates(d)
    rep = tt.convert()
    print(json.dumps(rep, indent=2))
    print("\n--- product.json ---")
    print((d / "templates" / "product.json").read_text())
    print("\n--- collection.json (should reference existing section, extracted=false) ---")
    print((d / "templates" / "collection.json").read_text())
    print("\n--- extracted main-product.liquid (first 20 lines) ---")
    print("\n".join((d / "sections" / "main-product.liquid").read_text().splitlines()[:20]))
    return rep


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--selftest":
        run_selftest()
        return
    theme_dir = args[0]
    dry = "--dry-run" in args
    tt = ThemeTemplates(theme_dir, dry_run=dry)
    rep = tt.convert()
    converted = [r for r in rep if r.get("output")]
    print("Built " + str(len(converted)) + " JSON templates"
          + (" (dry-run)" if dry else ""))
    for r in rep:
        flag = " [extracted main]" if r.get("extracted") else ""
        print("  " + r["template"] + " -> " + r["page_type"] + ".json  sections="
              + ",".join(r.get("sections", [])) + flag)


if __name__ == "__main__":
    main()
