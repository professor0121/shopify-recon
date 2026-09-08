#!/usr/bin/env python3
"""
FORM CLONER - Extract All Forms + Generate Liquid Form Templates
Extracts: form actions, methods, input fields, validation, select options
Generates: Liquid form templates with Shopify form tags

Usage: python3 form-cloner.py <input-dir> [output-dir]
"""

import json, sys, os, re
from datetime import datetime
from bs4 import BeautifulSoup


def extract_forms(html):
    """Extract all forms from HTML"""
    soup = BeautifulSoup(html, "lxml")
    forms = []
    
    for form in soup.find_all("form"):
        inputs = []
        for inp in form.find_all(["input", "select", "textarea", "button"]):
            field = {
                "tag": inp.name,
                "name": inp.get("name", ""),
                "type": inp.get("type", inp.name),
                "id": inp.get("id", ""),
                "class": " ".join(inp.get("class", [])),
                "placeholder": inp.get("placeholder", ""),
                "required": inp.get("required") is not None,
                "value": inp.get("value", "")[:50],
                "checked": inp.get("checked") is not None,
                "disabled": inp.get("disabled") is not None,
                "min": inp.get("min", ""),
                "max": inp.get("max", ""),
                "pattern": inp.get("pattern", ""),
                "label": "",
            }
            
            # Find associated label
            if field["id"]:
                label = soup.find("label", attrs={"for": field["id"]})
                if label:
                    field["label"] = label.get_text(strip=True)[:50]
            
            # Extract select options
            if inp.name == "select":
                options = []
                for opt in inp.find_all("option"):
                    options.append({
                        "value": opt.get("value", ""),
                        "text": opt.get_text(strip=True)[:50],
                        "selected": opt.get("selected") is not None,
                    })
                field["options"] = options
            
            # Button text
            if inp.name == "button":
                field["text"] = inp.get_text(strip=True)[:50]
            
            inputs.append(field)
        
        action = form.get("action", "")
        method = form.get("method", "get").lower()
        
        # Classify form type
        form_type = "custom"
        if "/cart/add" in action:
            form_type = "add_to_cart"
        elif "/cart" in action:
            form_type = "cart_update"
        elif "/search" in action:
            form_type = "search"
        elif "/contact" in action:
            form_type = "contact"
        elif "/account" in action:
            if "login" in action:
                form_type = "login"
            elif "register" in action:
                form_type = "register"
            else:
                form_type = "account"
        elif "newsletter" in form.get("class", []) or "newsletter" in str(form.get("id", "")).lower():
            form_type = "newsletter"
        
        forms.append({
            "action": action[:200],
            "method": method,
            "id": form.get("id", ""),
            "class": " ".join(form.get("class", [])),
            "type": form_type,
            "field_count": len(inputs),
            "fields": inputs,
        })
    
    return forms


def generate_liquid_form(form_data):
    """Generate Liquid form template from extracted form data"""
    
    form_type = form_data["type"]
    
    templates = {
        "add_to_cart": generate_add_to_cart_form(form_data),
        "search": generate_search_form(form_data),
        "newsletter": generate_newsletter_form(form_data),
        "contact": generate_contact_form(form_data),
        "cart_update": generate_cart_form(form_data),
    }
    
    return templates.get(form_type, generate_custom_form(form_data))


def generate_add_to_cart_form(form_data):
    return '''<!-- Add to Cart Form - Cloned from competitor -->
<form action="/cart/add" method="post" enctype="multipart/form-data" id="AddToCartForm" class="product-form">
  {% unless product.has_only_default_variant %}
    {% for option in product.options_with_values %}
      <div class="product-option">
        <label for="Option{{ option.position }}">{{ option.name }}</label>
        <select id="Option{{ option.position }}" name="options[{{ option.name | escape }}]">
          {% for value in option.values %}
            <option value="{{ value | escape }}" {% if option.selected_value == value %}selected{% endif %}>{{ value }}</option>
          {% endfor %}
        </select>
      </div>
    {% endfor %}
  {% endunless %}
  
  <div class="product-quantity">
    <label for="Quantity">Quantity</label>
    <input type="number" id="Quantity" name="quantity" value="1" min="1">
  </div>
  
  <input type="hidden" name="id" value="{{ product.selected_or_first_available_variant.id }}">
  
  <button type="submit" name="add" class="btn btn-add-to-cart" {% unless product.available %}disabled{% endunless %}>
    {% if product.available %}Add to Cart{% else %}Sold Out{% endif %}
  </button>
</form>'''


def generate_search_form(form_data):
    return '''<!-- Search Form - Cloned from competitor -->
<form action="/search" method="get" role="search" class="search-form">
  <input type="search" name="q" value="{{ search.terms | escape }}" 
         placeholder="Search products..." aria-label="Search">
  <button type="submit" aria-label="Search">Search</button>
</form>'''


def generate_newsletter_form(form_data):
    return '''<!-- Newsletter Form - Cloned from competitor -->
{% form 'customer' %}
  {% if form.posted_successfully? %}
    <p class="form-success">Thanks for subscribing!</p>
  {% endif %}
  <input type="hidden" name="contact[tags]" value="newsletter">
  <input type="email" name="contact[email]" placeholder="Your email" required>
  <button type="submit">Subscribe</button>
{% endform %}'''


def generate_contact_form(form_data):
    return '''<!-- Contact Form - Cloned from competitor -->
{% form 'contact' %}
  {% if form.posted_successfully? %}
    <p class="form-success">Thanks for reaching out!</p>
  {% endif %}
  
  {% if form.errors %}
    <div class="form-errors">{{ form.errors | default_errors }}</div>
  {% endif %}
  
  <input type="text" name="contact[name]" placeholder="Name" required>
  <input type="email" name="contact[email]" placeholder="Email" required>
  <input type="tel" name="contact[phone]" placeholder="Phone">
  <textarea name="contact[body]" placeholder="Message" required></textarea>
  <button type="submit">Send</button>
{% endform %}'''


def generate_cart_form(form_data):
    return '''<!-- Cart Form - Cloned from competitor -->
<form action="/cart" method="post" class="cart-form">
  {% for item in cart.items %}
    <div class="cart-item">
      <input type="number" name="updates[]" value="{{ item.quantity }}" min="0">
    </div>
  {% endfor %}
  
  {% if cart.note %}
    <textarea name="note" placeholder="Order note">{{ cart.note }}</textarea>
  {% endif %}
  
  <button type="submit" name="checkout">Checkout</button>
</form>'''


def generate_custom_form(form_data):
    fields_html = ""
    for field in form_data["fields"]:
        if field["tag"] == "input":
            required = " required" if field["required"] else ""
            placeholder = f' placeholder="{field["placeholder"]}"' if field["placeholder"] else ""
            label = f'<label>{field["label"]}</label>' if field["label"] else ""
            fields_html += f"  {label}\n  <input type=\"{field['type']}\" name=\"{field['name']}\"{placeholder}{required}>\n"
        elif field["tag"] == "select":
            options_html = "".join(f'<option value="{o["value"]}">{o["text"]}</option>' for o in field.get("options", []))
            fields_html += f'  <select name="{field["name"]}">{options_html}</select>\n'
        elif field["tag"] == "textarea":
            fields_html += f'  <textarea name="{field["name"]}" placeholder="{field["placeholder"]}"></textarea>\n'
        elif field["tag"] == "button":
            fields_html += f'  <button type="{field["type"]}">{field.get("text", "Submit")}</button>\n'
    
    return f'''<!-- Custom Form - Cloned from competitor -->
<form action="{form_data["action"]}" method="{form_data["method"]}" class="{form_data["class"]}">
{fields_html}
</form>'''


def main():
    if len(sys.argv) < 2:
        print("FORM CLONER")
        print("━" * 69)
        print("Usage: python3 form-cloner.py <input-dir> [output-dir]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "forms")
    
    html_path = os.path.join(input_dir, "homepage.html")
    with open(html_path) as f:
        html = f.read()
    
    print("FORM CLONER")
    print("━" * 69)
    
    forms = extract_forms(html)
    
    # Also check product page if available
    product_html_path = os.path.join(input_dir, "pages", "product.html")
    if os.path.exists(product_html_path):
        with open(product_html_path) as f:
            product_forms = extract_forms(f.read())
        forms.extend(product_forms)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    with open(os.path.join(output_dir, "forms.json"), "w") as f:
        json.dump(forms, f, indent=2)
    
    # Generate Liquid form snippets
    snippets_dir = os.path.join(output_dir, "snippets")
    os.makedirs(snippets_dir, exist_ok=True)
    
    for i, form in enumerate(forms):
        liquid = generate_liquid_form(form)
        filename = f"form-{form['type']}_{i}.liquid"
        with open(os.path.join(snippets_dir, filename), "w") as f:
            f.write(liquid)
    
    print(f"  Forms extracted: {len(forms)}")
    for form in forms:
        print(f"    • {form['type']}: {form['field_count']} fields (action={form['action'][:40]})")
    print(f"\n{len(forms)} form snippets generated in {snippets_dir}/")


if __name__ == "__main__":
    main()
