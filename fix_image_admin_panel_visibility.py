"""
Fix image admin panel visibility in templates/generate/new.html
"""

def fix_visibility():
    """Fix the visibility condition for image admin panel"""

    template_path = 'templates/generate/new.html'

    # Read the template
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the image admin panel
    panel_marker = 'id="image-models-admin-panel"'
    panel_pos = content.find(panel_marker)

    if panel_pos == -1:
        print("❌ Image admin panel not found")
        return

    # Find the style attribute with the wrong condition
    wrong_condition = 'style="{% if request.GET.type == \'video\' %}display:none{% endif %}"'

    # Replace with correct condition (show when NOT video mode)
    correct_condition = 'style="{% if request.GET.type != \'video\' %}display:block{% else %}display:none{% endif %}"'

    # Actually, simpler - just remove the inline style and let JavaScript handle it
    # Find the opening div tag
    div_start = content.rfind('<div', 0, panel_pos)
    div_end = content.find('>', panel_pos)

    if div_start == -1 or div_end == -1:
        print("❌ Could not find div tag")
        return

    # Extract the div tag
    div_tag = content[div_start:div_end+1]

    # Remove the style attribute
    new_div_tag = div_tag.replace('style="{% if request.GET.type == \'video\' %}display:none{% endif %}"', '')

    # Replace in content
    new_content = content[:div_start] + new_div_tag + content[div_end+1:]

    # Write back
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Fixed image admin panel visibility")
    print()
    print("Changes made:")
    print("  - Removed inline style condition")
    print("  - Panel will now be controlled by JavaScript")
    print()
    print("The panel should now be visible in image mode!")


if __name__ == '__main__':
    print("Fixing image admin panel visibility...")
    print()

    try:
        fix_visibility()
        print()
        print("✅ Done! Please refresh the page and check.")
        print()
        print("If still not visible:")
        print("1. Clear browser cache (Ctrl+Shift+R)")
        print("2. Check browser console for errors")
        print("3. Make sure you're logged in as admin (is_staff=True)")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
