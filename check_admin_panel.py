"""Check if admin panel was added correctly"""

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("Checking admin panel integration...")
print()

# Check HTML
html_found = 'image-models-admin-panel' in content
print(f"✓ HTML panel found: {html_found}")

# Check JavaScript
js_found = 'imageAdminPanel' in content
print(f"✓ JavaScript variable found: {js_found}")

# Find the panel location
if html_found:
    start = content.find('id="image-models-admin-panel"')
    if start != -1:
        # Get surrounding context
        context_start = max(0, start - 200)
        context_end = min(len(content), start + 200)
        context = content[context_start:context_end]
        print()
        print("Panel context:")
        print(context)

# Check if it's inside {% if request.user.is_staff %}
if html_found:
    panel_start = content.find('<!-- Admin Panel for Image Models')
    if panel_start != -1:
        # Look backwards for {% if request.user.is_staff %}
        before_panel = content[max(0, panel_start - 500):panel_start]
        has_staff_check = 'request.user.is_staff' in before_panel
        print()
        print(f"✓ Staff check found: {has_staff_check}")

print()
print("Recommendation:")
print("1. Clear browser cache (Ctrl+Shift+R)")
print("2. Make sure you're logged in as admin")
print("3. Check browser console for errors")
print("4. The panel should appear on /generate/new in image mode")
