#!/usr/bin/env python3
"""
ANIMATION/HOVER CLONER - Extract CSS Animations & Interactions
Extracts: transitions, transforms, keyframes, hover effects, scroll animations
Part of Shopify Recon | 2026-06-21

Usage: python3 animation-cloner.py <input-dir> [output-dir]
Example: python3 animation-cloner.py ./rothys-extract ./animations
"""

import json
import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# TRANSITION EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_transitions(html):
    """Extract all CSS transitions from inline styles and style blocks"""
    transitions = []
    
    # Extract from <style> blocks
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(style_blocks)
    
    # Also extract inline styles with transition
    inline_transitions = re.findall(r'style="[^"]*transition:\s*([^;"]+)', html)
    for t in inline_transitions:
        transitions.append({"source": "inline", "value": t.strip()})
    
    # From CSS blocks - find all selectors with transition property
    # Pattern: selector { ... transition: ...; ... }
    transition_pattern = re.compile(
        r'([^{]+)\{[^}]*transition\s*:\s*([^;}]+)[^}]*\}',
        re.DOTALL
    )
    
    for match in transition_pattern.finditer(all_css):
        selectors = match.group(1).strip()
        transition_value = match.group(2).strip()
        
        # Parse transition value
        parts = transition_value.split()
        parsed = {
            "selectors": [s.strip() for s in selectors.split(",")],
            "raw": transition_value,
        }
        
        if len(parts) >= 1:
            parsed["property"] = parts[0]
        if len(parts) >= 2:
            parsed["duration"] = parts[1]
        if len(parts) >= 3:
            # Could be timing function or delay
            if parts[2] in ["ease", "ease-in", "ease-out", "ease-in-out", "linear", "step-start", "step-end"]:
                parsed["timing_function"] = parts[2]
            else:
                parsed["delay"] = parts[2]
        if len(parts) >= 4:
            parsed["timing_function"] = parts[3] if parts[3] not in parsed.get("delay", "") else "ease"
        
        transitions.append({
            "source": "css_block",
            "selectors": parsed["selectors"],
            "property": parsed.get("property", "all"),
            "duration": parsed.get("duration", "0s"),
            "timing_function": parsed.get("timing_function", "ease"),
            "delay": parsed.get("delay", "0s"),
            "raw": parsed["raw"],
        })
    
    return transitions


# ═══════════════════════════════════════════════════════════════════
# TRANSFORM EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_transforms(html):
    """Extract CSS transforms"""
    transforms = []
    
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(style_blocks)
    
    # Inline transforms
    inline_transforms = re.findall(r'style="[^"]*transform:\s*([^;"]+)', html)
    for t in inline_transforms:
        transforms.append({"source": "inline", "value": t.strip()})
    
    # From CSS blocks
    transform_pattern = re.compile(
        r'([^{]+)\{[^}]*transform\s*:\s*([^;}]+)[^}]*\}',
        re.DOTALL
    )
    
    for match in transform_pattern.finditer(all_css):
        selectors = match.group(1).strip()
        transform_value = match.group(2).strip()
        
        # Classify transform type
        transform_type = "unknown"
        if "translate" in transform_value:
            transform_type = "translate"
        elif "rotate" in transform_value:
            transform_type = "rotate"
        elif "scale" in transform_value:
            transform_type = "scale"
        elif "skew" in transform_value:
            transform_type = "skew"
        elif "matrix" in transform_value:
            transform_type = "matrix"
        
        transforms.append({
            "source": "css_block",
            "selectors": [s.strip() for s in selectors.split(",")],
            "type": transform_type,
            "value": transform_value,
        })
    
    return transforms


# ═══════════════════════════════════════════════════════════════════
# KEYFRAME EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_keyframes(html):
    """Extract @keyframes animations"""
    keyframes = []
    
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(style_blocks)
    
    # Find @keyframes blocks - use balanced brace matching
    kf_pattern = re.compile(r'@keyframes\s+(\w[\w-]*)\s*\{', re.IGNORECASE)
    
    for match in kf_pattern.finditer(all_css):
        name = match.group(1)
        start = match.end()  # position after opening {
        
        # Find matching closing brace
        depth = 1
        pos = start
        while depth > 0 and pos < len(all_css):
            if all_css[pos] == '{':
                depth += 1
            elif all_css[pos] == '}':
                depth -= 1
            pos += 1
        
        body = all_css[start:pos-1]
        
        # Parse keyframe stops
        stops = []
        stop_pattern = re.compile(r'(\d+%|from|to)\s*\{([^}]*)\}', re.IGNORECASE)
        for stop_match in stop_pattern.finditer(body):
            stop = stop_match.group(1)
            props = stop_match.group(2).strip()
            stops.append({"stop": stop, "properties": props})
        
        keyframes.append({
            "name": name,
            "stops": stops,
            "raw": f"@keyframes {name} {{ {body[:300]} }}",
        })
    
    return keyframes


# ═══════════════════════════════════════════════════════════════════
# HOVER EFFECT EXTRACTOR
# ═══════════════════════════════════════════════════════════════════

def extract_hover_effects(html):
    """Extract :hover CSS rules"""
    hover_rules = []
    
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(style_blocks)
    
    # Find all :hover rules
    hover_pattern = re.compile(
        r'([^{]*?:hover[^{]*)\{([^}]*)\}',
        re.DOTALL
    )
    
    for match in hover_pattern.finditer(all_css):
        selector = match.group(1).strip()
        properties = match.group(2).strip()
        
        # Parse properties
        props = {}
        for prop_match in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', properties):
            prop_name = prop_match.group(1)
            prop_value = prop_match.group(2).strip()
            props[prop_name] = prop_value
        
        # Classify hover effect type
        effect_type = "style_change"
        if "transform" in props:
            if "scale" in props.get("transform", ""):
                effect_type = "scale"
            elif "translate" in props.get("transform", ""):
                effect_type = "move"
            elif "rotate" in props.get("transform", ""):
                effect_type = "rotate"
        elif "opacity" in props:
            effect_type = "fade"
        elif "background" in props:
            effect_type = "color_change"
        elif "box-shadow" in props:
            effect_type = "shadow"
        elif "border" in str(props):
            effect_type = "border_change"
        
        hover_rules.append({
            "selector": selector,
            "effect_type": effect_type,
            "properties": props,
            "raw": properties[:200],
        })
    
    return hover_rules


# ═══════════════════════════════════════════════════════════════════
# JS ANIMATION DETECTOR
# ═══════════════════════════════════════════════════════════════════

def extract_js_animations(html):
    """Detect JavaScript-based animations"""
    js_animations = {
        "intersection_observer": [],
        "request_animation_frame": [],
        "setInterval_animations": [],
        "scroll_handlers": [],
        "gsap_detected": False,
        "framer_motion_detected": False,
        "anime_js_detected": False,
        "aos_detected": False,  # Animate On Scroll
        "wow_js_detected": False,
    }
    
    # Intersection Observer (scroll animations)
    io_matches = re.findall(r'new\s+IntersectionObserver\(\s*(?:function|\([^)]*\)\s*=>)', html)
    js_animations["intersection_observer_count"] = len(io_matches)
    
    # requestAnimationFrame
    raf_matches = re.findall(r'requestAnimationFrame\(', html)
    js_animations["request_animation_frame_count"] = len(raf_matches)
    
    # scroll event handlers
    scroll_matches = re.findall(r'addEventListener\(\s*["\']scroll["\']', html)
    js_animations["scroll_handlers_count"] = len(scroll_matches)
    
    # Library detection
    if re.search(r'gsap\.|GreenSock|TweenMax|TweenLite|TimelineMax', html):
        js_animations["gsap_detected"] = True
    if re.search(r'framer-motion|useAnimation|motion\.', html):
        js_animations["framer_motion_detected"] = True
    if re.search(r'anime\(|anime\.js', html):
        js_animations["anime_js_detected"] = True
    if re.search(r'AOS\.init|data-aos=', html):
        js_animations["aos_detected"] = True
    if re.search(r'new\s+WOW|WOW\.init', html):
        js_animations["wow_js_detected"] = True
    
    # data-aos attributes (Animate On Scroll)
    aos_attrs = re.findall(r'data-aos="([^"]+)"', html)
    if aos_attrs:
        js_animations["aos_animations"] = dict(Counter(aos_attrs).most_common(10))
    
    return js_animations


# ═══════════════════════════════════════════════════════════════════
# ANIMATION SUMMARY + CSS GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_animation_css(transitions, transforms, keyframes, hover_effects):
    """Generate animations.css file from extracted data"""
    css = "/* animations.css - Generated by Shopify Recon Animation Cloner */\n"
    css += f"/* Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M')} */\n\n"
    
    # Keyframes
    if keyframes:
        css += "/* ═══ Keyframe Animations ═══ */\n\n"
        for kf in keyframes:
            css += f"@keyframes {kf['name']} {{\n"
            for stop in kf["stops"]:
                css += f"  {stop['stop']} {{ {stop['properties']} }}\n"
            css += "}\n\n"
    
    # Hover effects
    if hover_effects:
        css += "/* ═══ Hover Effects ═══ */\n\n"
        for hover in hover_effects:
            css += f"{hover['selector']} {{\n"
            for prop, value in hover["properties"].items():
                css += f"  {prop}: {value};\n"
            css += "}\n\n"
    
    # Transitions (deduplicated by selector)
    if transitions:
        css += "/* ═══ Transitions ═══ */\n\n"
        seen_selectors = set()
        for t in transitions:
            if t.get("source") != "css_block":
                continue
            for selector in t.get("selectors", []):
                if selector in seen_selectors:
                    continue
                seen_selectors.add(selector)
                css += f"{selector} {{\n"
                css += f"  transition: {t.get('property', 'all')} {t.get('duration', '0.3s')} {t.get('timing_function', 'ease')} {t.get('delay', '0s')};\n"
                css += "}\n\n"
    
    # Transforms
    if transforms:
        css += "/* ═══ Transforms ═══ */\n\n"
        seen_selectors = set()
        for t in transforms:
            if t.get("source") != "css_block":
                continue
            for selector in t.get("selectors", []):
                if selector in seen_selectors:
                    continue
                seen_selectors.add(selector)
                css += f"{selector} {{\n"
                css += f"  transform: {t['value']};\n"
                css += "}\n\n"
    
    return css


def analyze_animations(html):
    """Run full animation analysis"""
    transitions = extract_transitions(html)
    transforms = extract_transforms(html)
    keyframes = extract_keyframes(html)
    hover_effects = extract_hover_effects(html)
    js_animations = extract_js_animations(html)
    
    # Summarize
    summary = {
        "transitions_count": len(transitions),
        "transforms_count": len(transforms),
        "keyframes_count": len(keyframes),
        "hover_effects_count": len(hover_effects),
        "js_animations": js_animations,
    }
    
    # Categorize hover effects
    hover_types = Counter(h["effect_type"] for h in hover_effects)
    summary["hover_effect_types"] = dict(hover_types.most_common())
    
    # Categorize transforms
    transform_types = Counter(t.get("type", "unknown") for t in transforms if t.get("source") == "css_block")
    summary["transform_types"] = dict(transform_types.most_common())
    
    # Categorize transition durations
    durations = Counter(t.get("duration", "unknown") for t in transitions if t.get("source") == "css_block")
    summary["transition_durations"] = dict(durations.most_common(5))
    
    # List keyframe names
    summary["keyframe_names"] = [kf["name"] for kf in keyframes]
    
    return {
        "summary": summary,
        "transitions": transitions[:30],
        "transforms": transforms[:20],
        "keyframes": keyframes,
        "hover_effects": hover_effects[:30],
        "js_animations": js_animations,
    }


def main():
    if len(sys.argv) < 2:
        print("ANIMATION/HOVER CLONER")
        print("━" * 69)
        print()
        print("Usage: python3 animation-cloner.py <input-dir> [output-dir]")
        print("Example: python3 animation-cloner.py ./rothys-extract ./animations")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "animations")
    
    print("ANIMATION/HOVER CLONER")
    print("━" * 69)
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print()
    
    # Load HTML
    html_path = os.path.join(input_dir, "homepage.html")
    if not os.path.exists(html_path):
        print(f"No homepage.html in {input_dir}")
        sys.exit(1)
    
    with open(html_path) as f:
        html = f.read()
    
    print(f"  HTML loaded: {len(html)} bytes")
    
    print("  [1/5] Extracting transitions...")
    print("  [2/5] Extracting transforms...")
    print("  [3/5] Extracting keyframes...")
    print("  [4/5] Extracting hover effects...")
    print("  [5/5] Detecting JS animations...")
    
    result = analyze_animations(html)
    
    # Create output
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(output_dir, "animation-analysis.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    # Generate animations.css
    css = generate_animation_css(
        result["transitions"],
        result["transforms"],
        result["keyframes"],
        result["hover_effects"],
    )
    css_path = os.path.join(output_dir, "animations.css")
    with open(css_path, "w") as f:
        f.write(css)
    
    # Print report
    s = result["summary"]
    print(f"\nANIMATION EXTRACTION COMPLETE")
    print(f"━" * 69)
    print(f"  Output: {output_dir}/")
    print(f"  animation-analysis.json - Full analysis")
    print(f"  animations.css - Ready-to-use CSS")
    print()
    print(f"ANIMATION SUMMARY:")
    print(f"  • Transitions:      {s['transitions_count']}")
    print(f"  • Transforms:       {s['transforms_count']}")
    print(f"  • Keyframes:        {s['keyframes_count']}")
    print(f"  • Hover effects:    {s['hover_effects_count']}")
    print()
    
    if s.get("hover_effect_types"):
        print(f"   Hover Effect Types:")
        for effect_type, count in s["hover_effect_types"].items():
            print(f"     • {effect_type}: {count}")
    
    if s.get("transform_types"):
        print(f"\n  Transform Types:")
        for t_type, count in s["transform_types"].items():
            print(f"     • {t_type}: {count}")
    
    if s.get("transition_durations"):
        print(f"\n  ⏱ Transition Durations:")
        for duration, count in s["transition_durations"].items():
            print(f"     • {duration}: {count}")
    
    if s["keyframe_names"]:
        print(f"\n   Keyframe Animations:")
        for name in s["keyframe_names"]:
            print(f"     • {name}")
    
    js = s.get("js_animations", {})
    if js:
        print(f"\n  JS Animations:")
        print(f"     • Intersection Observer: {js.get('intersection_observer_count', 0)}")
        print(f"     • requestAnimationFrame: {js.get('request_animation_frame_count', 0)}")
        print(f"     • Scroll handlers: {js.get('scroll_handlers_count', 0)}")
        
        libs = []
        if js.get("gsap_detected"): libs.append("GSAP")
        if js.get("framer_motion_detected"): libs.append("Framer Motion")
        if js.get("anime_js_detected"): libs.append("Anime.js")
        if js.get("aos_detected"): libs.append("AOS (Animate On Scroll)")
        if js.get("wow_js_detected"): libs.append("WOW.js")
        
        if libs:
            print(f"\n  Animation Libraries Detected:")
            for lib in libs:
                print(f"     • {lib}")
        
        if js.get("aos_animations"):
            print(f"\n  AOS Animation Types Used:")
            for anim, count in js["aos_animations"].items():
                print(f"     • {anim}: {count}x")


if __name__ == "__main__":
    main()
