"""
Diagnose admin panel visibility issue
"""

def diagnose():
    """Check what's wrong with the admin panel"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find image admin panel
    image_panel_start = content.find('<!-- Admin Panel for Image Models')
    image_panel_end = content.find('<!-- End Admin Panel for Image Models')

    print("=" * 80)
    print("DIAGNOSTIC REPORT")
    print("=" * 80)
    print()

    if image_panel_start == -1:
        print("❌ Image admin panel NOT FOUND in template")
        return

    print("✅ Image admin panel FOUND in template")
    print(f"   Position: {image_panel_start} - {image_panel_end}")
    print()

    # Extract panel content
    panel_content = content[image_panel_start:image_panel_end + 50]

    # Check for staff condition
    staff_check = '{% if request.user.is_staff %}'
    has_staff_check = staff_check in panel_content

    print(f"{'✅' if has_staff_check else '❌'} Staff check found: {has_staff_check}")
    print()

    # Check for display style
    if 'display:none' in panel_content:
        print("⚠️  WARNING: 'display:none' found in panel")
        # Find the exact line
        lines = panel_content.split('\n')
        for i, line in enumerate(lines):
            if 'display:none' in line:
                print(f"   Line {i}: {line.strip()}")
    else:
        print("✅ No 'display:none' found")
    print()

    # Check for id
    if 'id="image-models-admin-panel"' in panel_content:
        print("✅ Panel ID found: image-models-admin-panel")
    else:
        print("❌ Panel ID NOT found")
    print()

    # Show first 300 chars of panel
    print("Panel preview (first 300 chars):")
    print("-" * 80)
    print(panel_content[:300])
    print("-" * 80)
    print()

    # Check JavaScript
    js_marker = 'imageAdminPanel'
    if js_marker in content:
        print(f"✅ JavaScript variable '{js_marker}' found")

        # Find the JS code
        js_start = content.find(js_marker)
        js_context = content[max(0, js_start - 200):js_start + 200]
        print()
        print("JavaScript context:")
        print("-" * 80)
        print(js_context)
        print("-" * 80)
    else:
        print(f"❌ JavaScript variable '{js_marker}' NOT found")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print()
    print("1. Make sure you're logged in as admin (is_staff=True)")
    print("2. Clear browser cache (Ctrl+Shift+R)")
    print("3. Check browser console for JavaScript errors (F12)")
    print("4. Make sure you're in IMAGE mode (not VIDEO mode)")
    print()


if __name__ == '__main__':
    diagnose()
