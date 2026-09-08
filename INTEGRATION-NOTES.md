# AI Website Cloner Integration - Shopify Recon

## Source
- **Repo:** https://github.com/JCodesMore/ai-website-cloner-template
- **Concept:** AI-powered website cloning using browser MCP + spec files + parallel builders
- **License:** MIT

## What We Adopted

### 1. Spec File System (from SKILL.md)
Every component gets a detailed specification BEFORE generation:
- Computed CSS values (exact, not estimated)
- Interaction model (static/click/scroll/time-driven)
- Multi-state extraction (default + hover + scroll + active)
- Responsive behavior (desktop/tablet/mobile)
- Real content (verbatim text, actual image URLs)

### 2. Component Extraction Script (from SKILL.md)
JavaScript extraction script that walks DOM tree and extracts:
- Every computed style property per element
- Child hierarchy (up to 4 levels deep)
- Images with natural dimensions
- Text content

### 3. Interaction Model Detection
Before building, determine if section is:
- Click-driven (tabs, buttons)
- Scroll-driven (IntersectionObserver, scroll-snap, sticky)
- Time-driven (auto-playing carousel)
- Hover-driven (dropdowns, tooltips)

### 4. Asset Discovery Script
JavaScript that enumerates ALL assets:
- Images (including layered/overlay compositions)
- Videos (with poster, autoplay, loop settings)
- Background images (CSS)
- SVG icons
- Fonts (computed families)
- Favicons

### 5. Multi-State Extraction
For stateful components:
- Capture State A (default)
- Trigger state change (click/scroll/hover)
- Capture State B
- Diff = behavior specification

### 6. Visual QA Diff
After clone, compare side-by-side:
- Desktop 1440px
- Mobile 390px
- Section-by-section comparison
- Interactive behavior test

## What We Adapted for Shopify Liquid

The original tool clones to **Next.js + React + Tailwind**.
We adapted the extraction methodology to output **Shopify Liquid templates**:

- `getComputedStyle()` extraction CSS variables in `theme.css`
- DOM structure `{% section %}` + `{% snippet %}` patterns
- Component spec `{% schema %}` blocks with settings
- Real content `{{ product.title }}`, `{{ collection.description }}`
- Interaction model `theme.js` with event listeners
- Multi-state CSS classes + JS toggle logic

## Integration Points

### shopify-recon.py (1-command entry point)
- Step 9: Animation/Hover extraction (from interaction sweep)
- Step 10: CSS injection (from design token extraction)
- Step 11 (NEW): Component spec generation
- Step 12 (NEW): Visual QA report

### deep-extractor-v2.py
- BeautifulSoup parsing = lightweight version of browser MCP DOM walking
- webcrack deobfuscation = JS logic extraction
- Asset mirroring = httrack-style download

### template-generator.py
- Component specs Liquid templates with exact CSS values
- Multi-state extraction conditional Liquid blocks
- Responsive behavior CSS media queries in theme.css
