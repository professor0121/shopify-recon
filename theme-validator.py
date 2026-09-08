#!/usr/bin/env python3
"""
Theme Validator - Validates generated Shopify theme against Shopify theme requirements.
Checks: required files, Liquid syntax, schema blocks, settings, JSON validity.
"""
import json, re, sys
from pathlib import Path

# Shopify theme required structure
REQUIRED_DIRS = ['layout', 'templates', 'sections', 'snippets', 'assets', 'config']
REQUIRED_LAYOUTS = ['theme.liquid']
REQUIRED_TEMPLATES = ['index', 'product', 'collection', 'cart', 'search', '404', 'page']
OPTIONAL_TEMPLATES = ['blog', 'article', 'list-collections', 'password', 'gift_card',
                      'customers/login', 'customers/register', 'customers/account',
                      'customers/reset_password', 'customers/activate_account',
                      'customers/addresses', 'customers/order']
REQUIRED_CONFIG = ['settings_schema.json']
REQUIRED_SCHEMA_SECTIONS = ['theme_info']
REQUIRED_SNIPPETS = []  # No mandatory snippets

class ThemeValidator:
    def __init__(self, theme_dir):
        self.theme_dir = Path(theme_dir)
        self.errors = []
        self.warnings = []
        self.passed = []
        self.stats = {
            'liquid_files': 0,
            'json_files': 0,
            'asset_files': 0,
            'total_files': 0,
            'total_size': 0,
            'schema_blocks': 0,
            'liquid_tags': 0,
            'liquid_variables': 0,
            'filters_used': set(),
        }
    
    def validate(self):
        print(f"\n{'='*60}")
        print(f"Theme Validator")
        print(f"Theme: {self.theme_dir}")
        print(f"{'='*60}\n")
        
        self.check_structure()
        self.check_layouts()
        self.check_templates()
        self.check_editor_readiness()
        self.check_sections()
        self.check_snippets()
        self.check_config()
        self.check_assets()
        self.check_liquid_syntax()
        self.check_schema_blocks()
        self.calculate_stats()
        self.print_report()
        
        return len(self.errors) == 0
    
    def check_structure(self):
        """Check required directories exist."""
        for d in REQUIRED_DIRS:
            dir_path = self.theme_dir / d
            if dir_path.exists():
                self.passed.append(f"Directory exists: {d}/")
            else:
                self.errors.append(f"Missing required directory: {d}/")
    
    def check_layouts(self):
        """Check required layout files."""
        layout_dir = self.theme_dir / "layout"
        if not layout_dir.exists():
            return
        
        for layout in REQUIRED_LAYOUTS:
            path = layout_dir / layout
            if path.exists():
                self.passed.append(f"Layout exists: layout/{layout}")
            else:
                self.errors.append(f"Missing required layout: layout/{layout}")
        
        # Check theme.liquid has required tags
        theme_liquid = layout_dir / "theme.liquid"
        if theme_liquid.exists():
            content = theme_liquid.read_text(encoding='utf-8', errors='replace')
            if '{{ content_for_header }}' not in content:
                self.errors.append("theme.liquid missing {{ content_for_header }}")
            else:
                self.passed.append("theme.liquid has content_for_header")
            
            if '{{ content_for_layout }}' not in content:
                self.errors.append("theme.liquid missing {{ content_for_layout }}")
            else:
                self.passed.append("theme.liquid has content_for_layout")
    
    def check_templates(self):
        """Check required template files (.json OR .liquid both valid)."""
        templates_dir = self.theme_dir / "templates"
        if not templates_dir.exists():
            return

        def has_template(tmpl):
            return ((templates_dir / (tmpl + ".json")).exists()
                    or (templates_dir / (tmpl + ".liquid")).exists())

        for tmpl in REQUIRED_TEMPLATES:
            if has_template(tmpl):
                ext = ".json" if (templates_dir / (tmpl + ".json")).exists() else ".liquid"
                self.passed.append("Template exists: templates/" + tmpl + ext)
            else:
                self.warnings.append("Missing recommended template: templates/" + tmpl)

        for tmpl in OPTIONAL_TEMPLATES:
            if has_template(tmpl):
                self.passed.append("Optional template exists: templates/" + tmpl)

    def check_editor_readiness(self):
        """Editor-Readiness Score: can a BUYER customize this theme?

        Premium themes are customizable in the theme editor. This checks the
        three pillars that make that possible:
          1. JSON templates  -> buyer can reorder/add/remove sections
          2. Section presets  -> sections appear in "Add section"
          3. Blocks + shopify_attributes -> buyer can drag/add/remove elements
        """
        templates_dir = self.theme_dir / "templates"
        sections_dir = self.theme_dir / "sections"
        self.editor = {
            "json_templates": 0,
            "liquid_templates": 0,
            "sections_total": 0,
            "sections_with_preset": 0,
            "sections_with_blocks": 0,
            "sections_with_shopify_attributes": 0,
            "app_block_support": 0,
            "score": 0,
            "notes": [],
        }

        # 1. JSON templates
        if templates_dir.exists():
            self.editor["json_templates"] = len(list(templates_dir.glob("*.json")))
            self.editor["liquid_templates"] = len(
                [p for p in templates_dir.glob("*.liquid")])
            if self.editor["json_templates"] == 0:
                self.warnings.append(
                    "EDITOR: 0 JSON templates - buyers cannot reorder/add/remove "
                    "sections on any page. Run json-template-builder.py.")
            else:
                self.passed.append(
                    "EDITOR: " + str(self.editor["json_templates"])
                    + " JSON templates (pages are reorderable)")

        # 2 + 3. Section presets / blocks / shopify_attributes
        if sections_dir.exists():
            secs = list(sections_dir.glob("*.liquid"))
            self.editor["sections_total"] = len(secs)
            for s in secs:
                c = s.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema",
                              c, re.DOTALL)
                schema = {}
                if m:
                    try:
                        schema = json.loads(m.group(1).strip())
                    except json.JSONDecodeError:
                        schema = {}
                if schema.get("presets"):
                    self.editor["sections_with_preset"] += 1
                if schema.get("blocks"):
                    self.editor["sections_with_blocks"] += 1
                    if any(isinstance(b, dict) and b.get("type") == "@app"
                           for b in schema["blocks"]):
                        self.editor["app_block_support"] += 1
                if "block.shopify_attributes" in c:
                    self.editor["sections_with_shopify_attributes"] += 1

        # Score: weighted across the three pillars (0-100)
        st = max(self.editor["sections_total"], 1)
        json_ok = 1.0 if self.editor["json_templates"] > 0 else 0.0
        preset_ratio = self.editor["sections_with_preset"] / st
        block_ratio = self.editor["sections_with_blocks"] / st
        attr_ratio = self.editor["sections_with_shopify_attributes"] / st
        score = (json_ok * 30 + preset_ratio * 25 + block_ratio * 25
                 + attr_ratio * 20)
        self.editor["score"] = round(score, 1)

        if self.editor["sections_with_preset"] == 0:
            self.warnings.append(
                "EDITOR: 0 sections have presets - none appear in 'Add section'.")
        if self.editor["sections_with_blocks"] == 0:
            self.warnings.append(
                "EDITOR: 0 sections expose blocks - buyers can't add/remove "
                "elements. Run block-ifier.py.")
        if self.editor["app_block_support"] > 0:
            self.passed.append(
                "EDITOR: @app blocks supported in "
                + str(self.editor["app_block_support"]) + " sections "
                "(buyers can plug in apps)")
    
    def check_sections(self):
        """Check section files and their schema blocks."""
        sections_dir = self.theme_dir / "sections"
        if not sections_dir.exists():
            self.warnings.append("No sections directory")
            return
        
        sections = list(sections_dir.glob("*.liquid"))
        if not sections:
            self.warnings.append("No section files found")
            return
        
        self.passed.append(f"Sections found: {len(sections)}")
        
        # Check each section has {% schema %}
        for section in sections:
            content = section.read_text(encoding='utf-8', errors='replace')
            if '{% schema %}' in content:
                self.stats['schema_blocks'] += 1
            else:
                self.warnings.append(f"Section without schema: {section.name}")
            
            # Check {% endschema %}
            if '{% schema %}' in content and '{% endschema %}' not in content:
                self.errors.append(f"Unclosed schema tag in: {section.name}")
    
    def check_snippets(self):
        """Check snippet files."""
        snippets_dir = self.theme_dir / "snippets"
        if not snippets_dir.exists():
            return
        
        snippets = list(snippets_dir.glob("*.liquid"))
        self.passed.append(f"Snippets found: {len(snippets)}")
    
    def check_config(self):
        """Check config files."""
        config_dir = self.theme_dir / "config"
        if not config_dir.exists():
            self.errors.append("Missing config directory")
            return
        
        # settings_schema.json
        schema_path = config_dir / "settings_schema.json"
        if schema_path.exists():
            try:
                with open(schema_path) as f:
                    schema = json.load(f)
                
                # Check theme_info
                has_theme_info = any(s.get('name') == 'theme_info' for s in schema)
                if has_theme_info:
                    self.passed.append("settings_schema.json has theme_info")
                else:
                    self.errors.append("settings_schema.json missing theme_info section")
                
                self.passed.append(f"settings_schema.json: {len(schema)} groups")
                
            except json.JSONDecodeError as e:
                self.errors.append(f"settings_schema.json invalid JSON: {e}")
        else:
            self.errors.append("Missing settings_schema.json")
        
        # settings_data.json
        data_path = config_dir / "settings_data.json"
        if data_path.exists():
            try:
                with open(data_path) as f:
                    data = json.load(f)
                
                if 'current' in data:
                    self.passed.append("settings_data.json has current settings")
                else:
                    self.warnings.append("settings_data.json missing 'current' key")
                
                if 'presets' in data:
                    self.passed.append(f"settings_data.json: {len(data['presets'])} presets")
                
            except json.JSONDecodeError as e:
                self.errors.append(f"settings_data.json invalid JSON: {e}")
        else:
            self.warnings.append("Missing settings_data.json (optional but recommended)")
    
    def check_assets(self):
        """Check asset files."""
        assets_dir = self.theme_dir / "assets"
        if not assets_dir.exists():
            self.warnings.append("No assets directory")
            return
        
        assets = list(assets_dir.glob("*"))
        self.stats['asset_files'] = len(assets)
        
        # Check for essential assets
        has_css = any(a.suffix == '.css' for a in assets)
        has_js = any(a.suffix == '.js' for a in assets)
        
        if has_css:
            self.passed.append("CSS assets found")
        else:
            self.warnings.append("No CSS assets found")
        
        if has_js:
            self.passed.append("JS assets found")
        else:
            self.warnings.append("No JS assets found")
    
    def check_liquid_syntax(self):
        """Check Liquid syntax in all .liquid files."""
        liquid_files = list(self.theme_dir.rglob("*.liquid"))
        self.stats['liquid_files'] = len(liquid_files)
        
        issues = 0
        for f in liquid_files:
            content = f.read_text(encoding='utf-8', errors='replace')
            rel_path = f.relative_to(self.theme_dir)
            
            # Check tag balance
            open_tags = len(re.findall(r'{%\s*(if|for|unless|case|form|schema|paginate|capture|tablerow|comment|raw|javascript|stylesheet)\s', content))
            close_tags = len(re.findall(r'{%\s*end(if|for|unless|case|form|schema|paginate|capture|tablerow|comment|raw|javascript|stylesheet)\s*%}', content))
            
            if open_tags != close_tags:
                self.warnings.append(f"Tag imbalance in {rel_path}: {open_tags} open, {close_tags} close")
                issues += 1
            
            # Count variables
            self.stats['liquid_variables'] += len(re.findall(r'{{\s*[^}]+\s*}}', content))
            
            # Count tags
            self.stats['liquid_tags'] += len(re.findall(r'{%\s*[^%]+\s*%}', content))
            
            # Collect filters
            filters = re.findall(r'\|\s*(\w+)', content)
            self.stats['filters_used'].update(filters)
            
            # Check for common errors
            if '===' in content:
                self.warnings.append(f"Possible JS comparison in Liquid: {rel_path}")
            
            # Unclosed string in output
            if re.search(r'{{[^}]*["\'][^}]*$', content, re.MULTILINE):
                self.warnings.append(f"Possible unclosed string in: {rel_path}")
        
        if issues == 0:
            self.passed.append(f"All {len(liquid_files)} Liquid files: tag balance OK")
    
    def check_schema_blocks(self):
        """Validate {% schema %} JSON blocks."""
        liquid_files = list(self.theme_dir.rglob("*.liquid"))
        
        for f in liquid_files:
            content = f.read_text(encoding='utf-8', errors='replace')
            rel_path = f.relative_to(self.theme_dir)
            
            # Extract schema blocks
            schema_match = re.search(r'{%\s*schema\s*%}(.*?){%\s*endschema\s*%}', content, re.DOTALL)
            if schema_match:
                schema_json = schema_match.group(1).strip()
                try:
                    schema = json.loads(schema_json)
                    
                    # Validate schema structure
                    if 'name' not in schema:
                        self.warnings.append(f"Schema missing 'name' in: {rel_path}")
                    if 'settings' not in schema and 'blocks' not in schema:
                        self.warnings.append(f"Schema has no settings or blocks: {rel_path}")
                    
                except json.JSONDecodeError as e:
                    self.errors.append(f"Invalid schema JSON in {rel_path}: {e}")
    
    def calculate_stats(self):
        """Calculate overall stats."""
        all_files = list(self.theme_dir.rglob("*"))
        self.stats['total_files'] = len([f for f in all_files if f.is_file()])
        self.stats['total_size'] = sum(f.stat().st_size for f in all_files if f.is_file())
        self.stats['json_files'] = len(list(self.theme_dir.rglob("*.json")))
        self.stats['filters_used'] = sorted(self.stats['filters_used'])
    
    def print_report(self):
        """Print validation report."""
        print(f"\n{'='*60}")
        print(f"VALIDATION REPORT")
        print(f"{'='*60}\n")
        
        # Errors
        if self.errors:
            print(f"ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"   {e}")
        else:
            print("No errors found!")
        
        # Warnings
        if self.warnings:
            print(f"\n WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    {w}")
        
        # Passed
        print(f"\nPASSED ({len(self.passed)}):")
        for p in self.passed:
            print(f"   {p}")
        
        # Stats
        print(f"\n{'='*60}")
        print(f"STATISTICS")
        print(f"{'='*60}")
        print(f"Total files:       {self.stats['total_files']}")
        print(f"  Liquid files:    {self.stats['liquid_files']}")
        print(f"  JSON files:      {self.stats['json_files']}")
        print(f"  Asset files:     {self.stats['asset_files']}")
        print(f"Total size:        {self.stats['total_size']:,} bytes ({self.stats['total_size']/1024/1024:.1f} MB)")
        print(f"Schema blocks:     {self.stats['schema_blocks']}")
        print(f"Liquid tags:       {self.stats['liquid_tags']}")
        print(f"Liquid variables:  {self.stats['liquid_variables']}")
        print(f"Filters used:      {len(self.stats['filters_used'])}")
        if isinstance(self.stats['filters_used'], list):
            print(f"  Filters:         {', '.join(self.stats['filters_used'])}")
        
        # Overall score
        total_checks = len(self.errors) + len(self.warnings) + len(self.passed)
        score = (len(self.passed) / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"THEME SCORE: {score:.1f}%")
        print(f"  Errors:   {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Passed:   {len(self.passed)}")

        # Editor-Readiness Score (buyer customizability)
        ed = getattr(self, "editor", None)
        if ed:
            print(f"\n{'='*60}")
            print(f"EDITOR-READINESS SCORE: {ed['score']:.1f}%  (can buyers customize?)")
            print(f"  JSON templates:            {ed['json_templates']} (reorderable pages)")
            print(f"  Sections w/ presets:       {ed['sections_with_preset']}/{ed['sections_total']} (in 'Add section')")
            print(f"  Sections w/ blocks:        {ed['sections_with_blocks']}/{ed['sections_total']} (add/remove elements)")
            print(f"  Sections w/ drag-handles:  {ed['sections_with_shopify_attributes']}/{ed['sections_total']} (shopify_attributes)")
            print(f"  @app block support:        {ed['app_block_support']} sections")
        
        if len(self.errors) == 0:
            print(f"\nTHEME IS VALID!")
        else:
            print(f"\n THEME HAS ERRORS - fix before pushing to Shopify")
        
        print(f"{'='*60}")
        
        # Write report
        report_path = self.theme_dir / "VALIDATION-REPORT.md"
        with open(report_path, 'w') as f:
            f.write(f"# Theme Validation Report\n\n")
            f.write(f"**Score: {score:.1f}%**\n\n")
            ed = getattr(self, "editor", None)
            if ed:
                f.write(f"**Editor-Readiness Score: {ed['score']:.1f}%** "
                        f"(can buyers customize the theme?)\n\n")
                f.write("| Editor pillar | Value |\n|---|---|\n")
                f.write(f"| JSON templates (reorderable pages) | {ed['json_templates']} |\n")
                f.write(f"| Sections with presets (in 'Add section') | {ed['sections_with_preset']}/{ed['sections_total']} |\n")
                f.write(f"| Sections with blocks (add/remove elements) | {ed['sections_with_blocks']}/{ed['sections_total']} |\n")
                f.write(f"| Sections with drag-handles (shopify_attributes) | {ed['sections_with_shopify_attributes']}/{ed['sections_total']} |\n")
                f.write(f"| @app block support | {ed['app_block_support']} sections |\n\n")
            f.write(f"## Errors ({len(self.errors)})\n\n")
            for e in self.errors:
                f.write(f"- {e}\n")
            f.write(f"\n## Warnings ({len(self.warnings)})\n\n")
            for w in self.warnings:
                f.write(f"- {w}\n")
            f.write(f"\n## Passed ({len(self.passed)})\n\n")
            for p in self.passed:
                f.write(f"- {p}\n")
            f.write(f"\n## Statistics\n\n")
            f.write(f"| Metric | Value |\n|--------|-------|\n")
            for k, v in self.stats.items():
                if k != 'filters_used':
                    f.write(f"| {k} | {v} |\n")
        
        print(f"\nReport: {report_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 theme-validator.py <theme_dir>")
        sys.exit(1)
    
    validator = ThemeValidator(sys.argv[1])
    valid = validator.validate()
    
    sys.exit(0 if valid else 1)

if __name__ == "__main__":
    main()
