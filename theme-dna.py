#!/usr/bin/env python3
"""
THEME DNA FINGERPRINTER - Detect Shopify Theme Framework
Identifies theme name, version, framework, and customization level from HTML
Part of Shopify Recon | 2026-06-21

Usage: python3 theme-dna.py <input-dir>
       python3 theme-dna.py --url=https://store.com
"""

import json
import sys
import os
import re
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# THEME FINGERPRINT DATABASE
# Each theme has unique signatures: schema_name, CSS classes, JS patterns,
# section types, file naming conventions, etc.
# ═══════════════════════════════════════════════════════════════════

THEME_DATABASE = {
    "dawn": {
        "name": "Dawn",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/dawn",
        "signatures": {
            "schema_name": [r"dawn", r"Dawn"],
            "css_classes": [r"page-width", r"section--padding", r"card--card"],
            "section_types": [r"image-banner", r"featured-collection", r"multicolumn", r"slideshow"],
            "js_patterns": [r"product-form\.js", r"cart\.js", r"prediction-request"],
            "file_patterns": [r"dawn/assets/", r"dawn/sections/"],
        },
        "popularity": "High (default Shopify theme)",
    },
    "turbo": {
        "name": "Turbo",
        "developer": "Out of the Sandbox",
        "price": "$450",
        "store_url": "https://outofthesandbox.com/products/turbo",
        "signatures": {
            "schema_name": [r"turbo", r"Turbo"],
            "css_classes": [r"turbo", r"js-product", r"product-section"],
            "section_types": [r"hero", r"collection-list", r"featured-content"],
            "js_patterns": [r"turbo\.js", r"theme\.js"],
            "file_patterns": [r"turbo/"],
        },
        "popularity": "Very High (premium best-seller)",
    },
    "prestige": {
        "name": "Prestige",
        "developer": "Maestrooo",
        "price": "$340",
        "store_url": "https://themes.shopify.com/themes/prestige",
        "signatures": {
            "schema_name": [r"prestige", r"Prestige"],
            "css_classes": [r"prestige", r"section-header", r"rte"],
            "section_types": [r"hero", r"featured-collections", r"multi-column"],
            "js_patterns": [r"prestige", r"theme\.js"],
        },
        "popularity": "High",
    },
    "motion": {
        "name": "Motion",
        "developer": "Archetype Themes",
        "price": "$360",
        "store_url": "https://themes.shopify.com/themes/motion",
        "signatures": {
            "schema_name": [r"^motion$", r"^Motion$"],
            "css_classes": [r"archetype", r"motion-hero", r"motion-slideshow"],
            "section_types": [r"motion-hero", r"motion-slideshow", r"motion-featured"],
            "js_patterns": [r"archetype-themes", r"archetype\.js", r"motion-theme"],
        },
        "popularity": "High",
    },
    "impulse": {
        "name": "Impulse",
        "developer": "Archetype Themes",
        "price": "$360",
        "store_url": "https://themes.shopify.com/themes/impulse",
        "signatures": {
            "schema_name": [r"impulse", r"Impulse"],
            "css_classes": [r"impulse", r"section--", r"hero__"],
            "section_types": [r"hero", r"slideshow", r"featured-collection", r"logo-list"],
            "js_patterns": [r"impulse", r"archetype"],
        },
        "popularity": "High",
    },
    "empire": {
        "name": "Empire",
        "developer": "Pixel Union",
        "price": "$320",
        "store_url": "https://themes.shopify.com/themes/empire",
        "signatures": {
            "schema_name": [r"empire", r"Empire"],
            "css_classes": [r"empire", r"hero-", r"product-grid"],
            "section_types": [r"hero", r"collection-list", r"featured-collection"],
            "js_patterns": [r"empire", r"pixel-union"],
        },
        "popularity": "Medium-High",
    },
    "symmetry": {
        "name": "Symmetry",
        "developer": "Pixel Union",
        "price": "$320",
        "store_url": "https://themes.shopify.com/themes/symmetry",
        "signatures": {
            "schema_name": [r"symmetry", r"Symmetry"],
            "css_classes": [r"symmetry", r"section-"],
            "js_patterns": [r"symmetry", r"pixel-union"],
        },
        "popularity": "Medium",
    },
    "pipeline": {
        "name": "Pipeline",
        "developer": "Groupthought",
        "price": "$320",
        "store_url": "https://themes.shopify.com/themes/pipeline",
        "signatures": {
            "schema_name": [r"pipeline", r"Pipeline"],
            "css_classes": [r"pipeline", r"section--"],
            "js_patterns": [r"pipeline", r"groupthought"],
        },
        "popularity": "Medium-High",
    },
    "debut": {
        "name": "Debut",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/debut",
        "signatures": {
            "schema_name": [r"debut", r"Debut"],
            "css_classes": [r"debut", r"hero__"],
            "section_types": [r"hero", r"featured-collection", r"image-bar"],
            "js_patterns": [r"debut", r"theme\.js"],
        },
        "popularity": "Medium (legacy, being deprecated)",
    },
    "narrative": {
        "name": "Narrative",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/narrative",
        "signatures": {
            "schema_name": [r"narrative", r"Narrative"],
            "css_classes": [r"narrative", r"hero-"],
            "js_patterns": [r"narrative"],
        },
        "popularity": "Medium",
    },
    "warehouse": {
        "name": "Warehouse",
        "developer": "Maestrooo",
        "price": "$340",
        "store_url": "https://themes.shopify.com/themes/warehouse",
        "signatures": {
            "schema_name": [r"warehouse", r"Warehouse"],
            "css_classes": [r"warehouse", r"product-list"],
            "js_patterns": [r"warehouse", r"maestrooo"],
        },
        "popularity": "Medium-High (large catalogs)",
    },
    "taste": {
        "name": "Taste",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/taste",
        "signatures": {
            "schema_name": [r"taste", r"Taste"],
            "css_classes": [r"taste", r"banner__"],
            "section_types": [r"image-banner", r"featured-collection", r"multicolumn"],
            "js_patterns": [r"taste"],
        },
        "popularity": "High (new default)",
    },
    "sense": {
        "name": "Sense",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/sense",
        "signatures": {
            "schema_name": [r"sense", r"Sense"],
            "css_classes": [r"sense", r"banner__"],
            "js_patterns": [r"sense"],
        },
        "popularity": "Medium",
    },
    "craft": {
        "name": "Craft",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/craft",
        "signatures": {
            "schema_name": [r"craft", r"Craft"],
            "css_classes": [r"craft", r"banner__"],
            "js_patterns": [r"craft"],
        },
        "popularity": "Medium",
    },
    "colorblock": {
        "name": "Colorblock",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/colorblock",
        "signatures": {
            "schema_name": [r"colorblock", r"Colorblock"],
            "js_patterns": [r"colorblock"],
        },
        "popularity": "New",
    },
    "spotlight": {
        "name": "Spotlight",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/spotlight",
        "signatures": {
            "schema_name": [r"spotlight", r"Spotlight"],
            "js_patterns": [r"spotlight"],
        },
        "popularity": "New",
    },
    # ═════════════════════════════════════════════════════════════
    # EXPANDED DATABASE - 35+ additional themes
    # ═════════════════════════════════════════════════════════════
    "atlantic": {
        "name": "Atlantic",
        "developer": "Pixel Union",
        "price": "$320",
        "store_url": "https://themes.shopify.com/themes/atlantic",
        "signatures": {
            "schema_name": [r"atlantic", r"Atlantic"],
            "css_classes": [r"atlantic", r"hero__", r"product-card"],
            "js_patterns": [r"atlantic", r"pixel-union"],
        },
        "popularity": "Medium",
    },
    "editorial": {
        "name": "Editorial",
        "developer": "Maestrooo",
        "price": "$340",
        "store_url": "https://themes.shopify.com/themes/editorial",
        "signatures": {
            "schema_name": [r"editorial", r"Editorial"],
            "css_classes": [r"editorial", r"section-header"],
            "js_patterns": [r"editorial", r"maestrooo"],
        },
        "popularity": "Medium",
    },
    "label": {
        "name": "Label",
        "developer": "Maestrooo",
        "price": "$340",
        "store_url": "https://themes.shopify.com/themes/label",
        "signatures": {
            "schema_name": [r"label", r"Label"],
            "css_classes": [r"label", r"section-header"],
            "js_patterns": [r"label", r"maestrooo"],
        },
        "popularity": "Medium",
    },
    "texas": {
        "name": "Texas",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"texas", r"Texas"],
            "js_patterns": [r"texas", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "district": {
        "name": "District",
        "developer": "Pixel Union",
        "price": "$320",
        "store_url": "https://themes.shopify.com/themes/district",
        "signatures": {
            "schema_name": [r"district", r"District"],
            "css_classes": [r"district", r"hero-"],
            "js_patterns": [r"district", r"pixel-union"],
        },
        "popularity": "Medium",
    },
    "enza": {
        "name": "Enza",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"enza", r"Enza"],
            "js_patterns": [r"enza", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "vantage": {
        "name": "Vantage",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"vantage", r"Vantage"],
            "js_patterns": [r"vantage", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "trademark": {
        "name": "Trademark",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"trademark", r"Trademark"],
            "js_patterns": [r"trademark", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "cascade": {
        "name": "Cascade",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"cascade", r"Cascade"],
            "js_patterns": [r"cascade", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "gravity": {
        "name": "Gravity",
        "developer": "Groupthought",
        "price": "$320",
        "signatures": {
            "schema_name": [r"gravity", r"Gravity"],
            "js_patterns": [r"gravity", r"groupthought"],
        },
        "popularity": "Low",
    },
    "feature": {
        "name": "Feature",
        "developer": "Groupthought",
        "price": "$320",
        "signatures": {
            "schema_name": [r"feature", r"Feature"],
            "js_patterns": [r"feature", r"groupthought"],
        },
        "popularity": "Low",
    },
    "masonry": {
        "name": "Masonry",
        "developer": "Groupthought",
        "price": "$320",
        "signatures": {
            "schema_name": [r"masonry", r"Masonry"],
            "js_patterns": [r"masonry", r"groupthought"],
        },
        "popularity": "Low",
    },
    "icon": {
        "name": "Icon",
        "developer": "Underground",
        "price": "$320",
        "signatures": {
            "schema_name": [r"^icon$", r"^Icon$"],
            "js_patterns": [r"icon-theme", r"underground"],
        },
        "popularity": "Low",
    },
    "parallax": {
        "name": "Parallax",
        "developer": "Out of the Sandbox",
        "price": "$450",
        "store_url": "https://outofthesandbox.com/products/parallax",
        "signatures": {
            "schema_name": [r"parallax", r"Parallax"],
            "css_classes": [r"parallax", r"js-product"],
            "js_patterns": [r"parallax", r"out-of-the-sandbox"],
        },
        "popularity": "Medium-High",
    },
    "responsive": {
        "name": "Responsive",
        "developer": "Out of the Sandbox",
        "price": "$450",
        "signatures": {
            "schema_name": [r"responsive", r"Responsive"],
            "css_classes": [r"responsive", r"js-product"],
            "js_patterns": [r"responsive", r"out-of-the-sandbox"],
        },
        "popularity": "Medium-High",
    },
    "mobilia": {
        "name": "Mobilia",
        "developer": "Out of the Sandbox",
        "price": "$450",
        "signatures": {
            "schema_name": [r"mobilia", r"Mobilia"],
            "js_patterns": [r"mobilia", r"out-of-the-sandbox"],
        },
        "popularity": "Medium",
    },
    "liquid": {
        "name": "Liquid",
        "developer": "Out of the Sandbox",
        "price": "$450",
        "signatures": {
            "schema_name": [r"^liquid$", r"^Liquid$"],
            "js_patterns": [r"liquid-theme", r"out-of-the-sandbox"],
        },
        "popularity": "Low",
    },
    "express": {
        "name": "Express",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"^express$", r"^Express$"],
            "js_patterns": [r"express", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "foodie": {
        "name": "Foodie",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"foodie", r"Foodie"],
            "js_patterns": [r"foodie", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "palo Alto": {
        "name": "Palo Alto",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"palo.?alto", r"Palo.?Alto"],
            "js_patterns": [r"palo-alto", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "showtime": {
        "name": "Showtime",
        "developer": "Underground",
        "price": "$320",
        "signatures": {
            "schema_name": [r"showtime", r"Showtime"],
            "js_patterns": [r"showtime", r"underground"],
        },
        "popularity": "Low",
    },
    "blockshop": {
        "name": "Blockshop",
        "developer": "Underground",
        "price": "$320",
        "signatures": {
            "schema_name": [r"blockshop", r"Blockshop", r"block-shop"],
            "js_patterns": [r"blockshop", r"underground"],
        },
        "popularity": "Low-Medium",
    },
    "kingdom": {
        "name": "Kingdom",
        "developer": "Krown Themes",
        "price": "$320",
        "signatures": {
            "schema_name": [r"kingdom", r"Kingdom"],
            "js_patterns": [r"kingdom", r"krown"],
        },
        "popularity": "Low",
    },
    "split": {
        "name": "Split",
        "developer": "Krown Themes",
        "price": "$320",
        "signatures": {
            "schema_name": [r"^split$", r"^Split$"],
            "js_patterns": [r"split-theme", r"krown"],
        },
        "popularity": "Low",
    },
    "framework": {
        "name": "Framework",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"framework", r"Framework"],
            "js_patterns": [r"framework", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "canopy": {
        "name": "Canopy",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"canopy", r"Canopy"],
            "js_patterns": [r"canopy", r"pixel-union"],
        },
        "popularity": "Low-Medium",
    },
    " Launch": {
        "name": "Launch",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"^launch$", r"^Launch$"],
            "js_patterns": [r"launch", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "edition": {
        "name": "Edition",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"edition", r"Edition"],
            "js_patterns": [r"edition", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "merchant": {
        "name": "Merchant",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"merchant", r"Merchant"],
            "js_patterns": [r"merchant", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "superstore": {
        "name": "Superstore",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"superstore", r"Superstore"],
            "js_patterns": [r"superstore", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "focal": {
        "name": "Focal",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"focal", r"Focal"],
            "js_patterns": [r"focal", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "context": {
        "name": "Context",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"context", r"Context"],
            "js_patterns": [r"context", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "seattle": {
        "name": "Seattle",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"seattle", r"Seattle"],
            "js_patterns": [r"seattle", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "uxshop": {
        "name": "UX Shop",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"uxshop", r"UX.Shop", r"ux-shop"],
            "js_patterns": [r"uxshop", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "broadcast": {
        "name": "Broadcast",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"broadcast", r"Broadcast"],
            "js_patterns": [r"broadcast", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "combine": {
        "name": "Combine",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"combine", r"Combine"],
            "js_patterns": [r"combine", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "slowdown": {
        "name": "Slowdown",
        "developer": "Maestrooo",
        "price": "$340",
        "signatures": {
            "schema_name": [r"slowdown", r"Slowdown"],
            "js_patterns": [r"slowdown", r"maestrooo"],
        },
        "popularity": "Low",
    },
    "california": {
        "name": "California",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"california", r"California"],
            "js_patterns": [r"california", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "startup": {
        "name": "Startup",
        "developer": "Pixel Union",
        "price": "$320",
        "signatures": {
            "schema_name": [r"startup", r"Startup"],
            "js_patterns": [r"startup", r"pixel-union"],
        },
        "popularity": "Low",
    },
    "supply": {
        "name": "Supply",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/supply",
        "signatures": {
            "schema_name": [r"supply", r"Supply"],
            "css_classes": [r"supply"],
            "js_patterns": [r"supply"],
        },
        "popularity": "Medium (large catalogs)",
    },
    "boundless": {
        "name": "Boundless",
        "developer": "Shopify (Official)",
        "price": "Free",
        "store_url": "https://themes.shopify.com/themes/boundless",
        "signatures": {
            "schema_name": [r"boundless", r"Boundless"],
            "css_classes": [r"boundless"],
            "js_patterns": [r"boundless"],
        },
        "popularity": "Medium",
    },
    "debutify": {
        "name": "Debutify",
        "developer": "Debutify",
        "price": "Free",
        "store_url": "https://debutify.com",
        "signatures": {
            "schema_name": [r"debutify", r"Debutify"],
            "css_classes": [r"debutify", r"df-"],
            "js_patterns": [r"debutify", r"df-"],
        },
        "popularity": "High (free with features)",
    },
    "booster": {
        "name": "Booster Theme",
        "developer": "Booster Theme",
        "price": "$499",
        "store_url": "https://boostertheme.com",
        "signatures": {
            "schema_name": [r"booster", r"Booster"],
            "css_classes": [r"booster"],
            "js_patterns": [r"booster"],
        },
        "popularity": "Medium-High (conversion-focused)",
    },
    "shoptimized": {
        "name": "Shoptimized",
        "developer": "Shoptimized",
        "price": "$297",
        "store_url": "https://shoptimized.net",
        "signatures": {
            "schema_name": [r"shoptimized", r"Shoptimized"],
            "css_classes": [r"shoptimized"],
            "js_patterns": [r"shoptimized"],
        },
        "popularity": "Medium (conversion-focused)",
    },
    "ecomturbo": {
        "name": "eCom Turbo",
        "developer": "eCom Turbo",
        "price": "$197",
        "signatures": {
            "schema_name": [r"ecom.?turbo", r"eCom.?Turbo"],
            "css_classes": [r"ecom-turbo"],
            "js_patterns": [r"ecom-turbo"],
        },
        "popularity": "Low-Medium",
    },
    "fastor": {
        "name": "Fastor",
        "developer": "Fastor",
        "price": "$69",
        "signatures": {
            "schema_name": [r"fastor", r"Fastor"],
            "css_classes": [r"fastor"],
            "js_patterns": [r"fastor"],
        },
        "popularity": "Medium (ThemeForest)",
    },
    "elessi": {
        "name": "Elessi",
        "developer": "NasaTheme",
        "price": "$89",
        "signatures": {
            "schema_name": [r"elessi", r"Elessi"],
            "css_classes": [r"elessi", r"nasa-"],
            "js_patterns": [r"elessi", r"nasa-"],
        },
        "popularity": "Medium (ThemeForest)",
    },
    "basel": {
        "name": "Basel",
        "developer": "ThemeRoad",
        "price": "$69",
        "signatures": {
            "schema_name": [r"^basel$", r"^Basel$"],
            "css_classes": [r"basel", r"basel-"],
            "js_patterns": [r"basel"],
        },
        "popularity": "Medium (ThemeForest)",
    },
    "flatsome": {
        "name": "Flatsome",
        "developer": "UX Themes",
        "price": "$69",
        "signatures": {
            "schema_name": [r"flatsome", r"Flatsome"],
            "css_classes": [r"flatsome", r"ux-"],
            "js_patterns": [r"flatsome", r"ux-"],
        },
        "popularity": "High (ThemeForest best-seller)",
    },
    "porto": {
        "name": "Porto",
        "developer": "Porto",
        "price": "$69",
        "signatures": {
            "schema_name": [r"^porto$", r"^Porto$"],
            "css_classes": [r"porto", r"porto-"],
            "js_patterns": [r"porto"],
        },
        "popularity": "High (ThemeForest)",
    },
}


# ═══════════════════════════════════════════════════════════════════
# THEME DETECTOR
# ═══════════════════════════════════════════════════════════════════

class ThemeDNA:
    """Detect and fingerprint Shopify theme from HTML"""
    
    def __init__(self, html):
        self.html = html
        self.detections = []
    
    def extract_shopify_theme(self):
        """Extract Shopify.theme JS object"""
        # Try to find Shopify.theme = {...}
        match = re.search(r'Shopify\.theme\s*=\s*(\{[^}]+\})', self.html)
        if match:
            try:
                theme_obj = json.loads(match.group(1).replace("'", '"'))
                return {
                    "name": theme_obj.get("name", "Unknown"),
                    "id": theme_obj.get("id", None),
                    "schema_name": theme_obj.get("schema_name", None),
                    "schema_version": theme_obj.get("schema_version", None),
                    "theme_store_id": theme_obj.get("theme_store_id", None),
                    "role": theme_obj.get("role", "main"),
                }
            except json.JSONDecodeError:
                # Try manual parsing
                name_match = re.search(r'"name"\s*:\s*"([^"]+)"', match.group(1))
                schema_match = re.search(r'"schema_name"\s*:\s*"([^"]+)"', match.group(1))
                version_match = re.search(r'"schema_version"\s*:\s*"([^"]+)"', match.group(1))
                return {
                    "name": name_match.group(1) if name_match else "Unknown",
                    "id": None,
                    "schema_name": schema_match.group(1) if schema_match else None,
                    "schema_version": version_match.group(1) if version_match else None,
                    "theme_store_id": None,
                    "role": "main",
                }
        return None
    
    def detect_theme_store_id(self):
        """Detect theme_store_id - if present, it's a Shopify Theme Store theme"""
        match = re.search(r'theme_store_id["\s:]+(\d+)', self.html)
        if match:
            return int(match.group(1))
        match = re.search(r'theme_store_id["\s:]+null', self.html)
        if match:
            return None
        return None
    
    def match_fingerprints(self):
        """Match HTML against theme fingerprint database"""
        theme_data = self.extract_shopify_theme()
        matches = []
        
        for theme_key, theme_info in THEME_DATABASE.items():
            score = 0
            evidence = []
            
            # Check schema_name
            if theme_data and theme_data.get("schema_name"):
                for pattern in theme_info["signatures"].get("schema_name", []):
                    if re.search(pattern, theme_data["schema_name"], re.IGNORECASE):
                        score += 50
                        evidence.append(f"schema_name matches: '{theme_data['schema_name']}' ~ /{pattern}/")
            
            # Check theme name
            if theme_data and theme_data.get("name"):
                for pattern in theme_info["signatures"].get("schema_name", []):
                    if re.search(pattern, theme_data["name"], re.IGNORECASE):
                        score += 30
                        evidence.append(f"theme name matches: '{theme_data['name']}' ~ /{pattern}/")
            
            # Check CSS classes
            for pattern in theme_info["signatures"].get("css_classes", []):
                matches_count = len(re.findall(pattern, self.html, re.IGNORECASE))
                if matches_count > 0:
                    score += min(matches_count * 5, 20)
                    evidence.append(f"CSS class '{pattern}' found {matches_count}x")
            
            # Check section types
            for pattern in theme_info["signatures"].get("section_types", []):
                matches_count = len(re.findall(pattern, self.html, re.IGNORECASE))
                if matches_count > 0:
                    score += min(matches_count * 5, 20)
                    evidence.append(f"Section type '{pattern}' found {matches_count}x")
            
            # Check JS patterns
            for pattern in theme_info["signatures"].get("js_patterns", []):
                matches_count = len(re.findall(pattern, self.html, re.IGNORECASE))
                if matches_count > 0:
                    score += min(matches_count * 3, 15)
                    evidence.append(f"JS pattern '{pattern}' found {matches_count}x")
            
            # Check file patterns (CDN asset URLs)
            for pattern in theme_info["signatures"].get("file_patterns", []):
                matches_count = len(re.findall(pattern, self.html, re.IGNORECASE))
                if matches_count > 0:
                    score += min(matches_count * 5, 15)
                    evidence.append(f"File pattern '{pattern}' found {matches_count}x")
            
            if score > 0:
                matches.append({
                    "theme_key": theme_key,
                    "name": theme_info.get("name", theme_key),
                    "developer": theme_info.get("developer", "Unknown"),
                    "price": theme_info.get("price", "Unknown"),
                    "store_url": theme_info.get("store_url", ""),
                    "popularity": theme_info.get("popularity", "Unknown"),
                    "score": score,
                    "evidence": evidence,
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches
    
    def detect_custom_theme(self, theme_data):
        """Detect if store uses a custom (non-Theme-Store) theme"""
        if not theme_data:
            return {"is_custom": True, "reason": "No Shopify.theme object found (heavily customized or headless)"}
        
        if theme_data.get("theme_store_id") is None:
            return {"is_custom": True, "reason": f"theme_store_id is null - custom theme '{theme_data.get('name', 'Unknown')}'"}
        
        return {"is_custom": False, "reason": f"Theme Store ID: {theme_data['theme_store_id']}"}
    
    def detect_customization_level(self, theme_data, fingerprint_matches):
        """Estimate how customized the theme is"""
        if not theme_data:
            return "Heavily Customized / Headless"
        
        if not fingerprint_matches or fingerprint_matches[0]["score"] < 30:
            return "Fully Custom Build"
        
        top_score = fingerprint_matches[0]["score"]
        
        # Check for additional custom sections
        section_ids = set(re.findall(r'shopify-section-template--\d+__(\w+?)_', self.html))
        known_section_types = set()
        for m in fingerprint_matches[:1]:
            for sig in THEME_DATABASE.get(m["theme_key"], {}).get("signatures", {}).get("section_types", []):
                known_section_types.add(sig.replace("\\", "").replace("r'", "").replace("'", ""))
        
        custom_sections = section_ids - known_section_types
        
        if top_score > 80 and len(custom_sections) <= 2:
            return "Light Customization (mostly stock)"
        elif top_score > 50:
            return f"Moderate Customization ({len(custom_sections)} custom sections)"
        elif top_score > 20:
            return f"Heavy Customization ({len(custom_sections)} custom sections)"
        else:
            return "Heavily Customized"
    
    def analyze(self):
        """Run full theme DNA analysis"""
        theme_data = self.extract_shopify_theme()
        fingerprint_matches = self.match_fingerprints()
        custom_info = self.detect_custom_theme(theme_data)
        customization = self.detect_customization_level(theme_data, fingerprint_matches)
        
        # Determine detected theme
        if fingerprint_matches and fingerprint_matches[0]["score"] >= 30:
            detected_theme = fingerprint_matches[0]["name"]
            detected_developer = fingerprint_matches[0]["developer"]
            detected_price = fingerprint_matches[0]["price"]
            confidence = min(fingerprint_matches[0]["score"], 100)
        elif theme_data and theme_data.get("name"):
            detected_theme = theme_data["name"]
            detected_developer = "Custom / In-house"
            detected_price = "N/A (custom)"
            confidence = 50 if custom_info["is_custom"] else 80
        else:
            detected_theme = "Unknown"
            detected_developer = "Unknown"
            detected_price = "Unknown"
            confidence = 0
        
        # Extract section count
        section_count = len(set(re.findall(r'shopify-section-(?:template--\d+__)?(\w+?)(?:_[A-Za-z0-9]+)?["\s]', self.html)))
        
        # Detect tech stack
        tech_stack = []
        if re.search(r'__NEXT_DATA__|next\.js|_next/', self.html, re.IGNORECASE):
            tech_stack.append("Next.js")
        if re.search(r'react|ReactDOM', self.html, re.IGNORECASE):
            tech_stack.append("React")
        if re.search(r'vue|Vue', self.html, re.IGNORECASE):
            tech_stack.append("Vue.js")
        if re.search(r'jquery|jQuery', self.html, re.IGNORECASE):
            tech_stack.append("jQuery")
        if re.search(r'tailwind|tw-', self.html, re.IGNORECASE):
            tech_stack.append("Tailwind CSS")
        if re.search(r'window\.Shopify', self.html):
            tech_stack.append("Shopify (native)")
        if not tech_stack:
            tech_stack.append("Vanilla JS")
        
        return {
            "detected_theme": detected_theme,
            "developer": detected_developer,
            "price": detected_price,
            "confidence": confidence,
            "is_custom": custom_info["is_custom"],
            "customization_level": customization,
            "theme_store_id": theme_data.get("theme_store_id") if theme_data else None,
            "schema_name": theme_data.get("schema_name") if theme_data else None,
            "schema_version": theme_data.get("schema_version") if theme_data else None,
            "theme_name_raw": theme_data.get("name") if theme_data else None,
            "section_count": section_count,
            "tech_stack": tech_stack,
            "fingerprint_matches": fingerprint_matches[:3],
            "custom_info": custom_info,
            "analyzed_at": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════
# CLI OUTPUT
# ═══════════════════════════════════════════════════════════════════

def print_report(dna):
    """Print beautiful DNA report"""
    confidence_bar = "█" * (dna["confidence"] // 10) + "░" * (10 - dna["confidence"] // 10)
    
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║  THEME DNA FINGERPRINT REPORT                                   ║")
    print("╠═══════════════════════════════════════════════════════════════════╣")
    print("║                                                                    ║")
    print(f"║  Detected Theme:    {dna['detected_theme']:<44}║")
    print(f"║  Developer:         {dna['developer']:<44}║")
    print(f"║  Price:             {dna['price']:<44}║")
    print(f"║  Custom:            {'Yes' if dna['is_custom'] else 'No (Theme Store)':<44}║")
    print(f"║  Customization:     {dna['customization_level']:<44}║")
    print("║                                                                    ║")
    print(f"║  Confidence:        [{confidence_bar}] {dna['confidence']}%{'':<{max(0, 14 - len(str(dna['confidence'])))}}║")
    print("║                                                                    ║")
    if dna["schema_name"]:
        print(f"║  Schema Name:       {dna['schema_name']:<44}║")
    if dna["schema_version"]:
        print(f"║  Schema Version:    {dna['schema_version']:<44}║")
    if dna["theme_name_raw"]:
        print(f"║  Raw Theme Name:    {dna['theme_name_raw']:<44}║")
    print(f"║   Sections:          {str(dna['section_count']):<44}║")
    print("║                                                                    ║")
    print("║  Tech Stack:                                                    ║")
    for tech in dna["tech_stack"]:
        print(f"║     • {tech:<52}║")
    print("║                                                                    ║")
    if dna["fingerprint_matches"]:
        print("║  Fingerprint Matches:                                           ║")
        for m in dna["fingerprint_matches"][:3]:
            print(f"║     • {m['name']} ({m['developer']}) - Score: {m['score']:<3}{'':<{max(0, 30 - len(m['name']) - len(m['developer']) - len(str(m['score'])))}}║")
        print("║                                                                    ║")
    if dna["fingerprint_matches"] and dna["fingerprint_matches"][0]["evidence"]:
        print("║  Evidence:                                                      ║")
        for e in dna["fingerprint_matches"][0]["evidence"][:5]:
            print(f"║     • {e[:52]:<52}║")
        print("║                                                                    ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    # Custom info
    if dna["is_custom"]:
        print()
        print(f"  {dna['custom_info']['reason']}")
        print(f"  Customization level: {dna['customization_level']}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Theme DNA Fingerprinter")
    parser.add_argument("input", nargs="?", help="Input directory with homepage.html")
    parser.add_argument("--url", help="Shopify store URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Output directory for report")
    
    args = parser.parse_args()
    
    html = ""
    
    if args.url:
        # Fetch from URL
        import subprocess
        url = args.url if args.url.startswith("http") else "https://" + args.url
        print(f"Fetching: {url}")
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", "Mozilla/5.0", "--max-time", "15", url],
            capture_output=True, text=True
        )
        html = result.stdout
    elif args.input:
        html_path = os.path.join(args.input, "homepage.html")
        if not os.path.exists(html_path):
            print(f"No homepage.html in {args.input}")
            sys.exit(1)
        with open(html_path) as f:
            html = f.read()
    else:
        parser.print_help()
        sys.exit(1)
    
    if not html or len(html) < 1000:
        print("Could not get HTML content")
        sys.exit(1)
    
    dna = ThemeDNA(html).analyze()
    
    if args.json:
        print(json.dumps(dna, indent=2))
    else:
        print_report(dna)
    
    # Save to file if output specified
    if args.output:
        os.makedirs(args.output, exist_ok=True)
        with open(os.path.join(args.output, "theme-dna.json"), "w") as f:
            json.dump(dna, f, indent=2)
        print(f"\nSaved: {args.output}/theme-dna.json")


if __name__ == "__main__":
    main()
