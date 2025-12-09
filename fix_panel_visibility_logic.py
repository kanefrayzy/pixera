"""
Fix panel visibility logic in templates/generate/new.html
The image panel should show in IMAGE mode, not VIDEO mode
"""

def fix_visibility():
    """Fix the JavaScript logic for panel visibility"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the JavaScript that controls panel visibility
    js_marker = 'const imageAdminPanel'
    js_pos = content.find(js_marker)

    if js_pos == -1:
        print("❌ JavaScript for panel visibility not found")
        return False

    # Find the line that sets the display
    # Current (wrong): imageAdminPanel.style.display=isImage?'none':'block'
    # Should be:       imageAdminPanel.style.display=isImage?'block':'none'

    wrong_logic = "imageAdminPanel.style.display=isImage?'none':'block'"
    correct_logic = "imageAdminPanel.style.display=isImage?'block':'none'"

    if wrong_logic in content:
        content = content.replace(wrong_logic, correct_logic)
        print("✅ Fixed panel visibility logic")
        print()
        print("Changed:")
        print(f"  FROM: {wrong_logic}")
        print(f"  TO:   {correct_logic}")
    else:
        print("⚠️  Logic already correct or not found")
        return False

    # Write back
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print()
    print("✅ Panel visibility logic fixed!")
    print()
    print("Now the image panel will show when in IMAGE mode")
    print("and hide when in VIDEO mode")

    return True


if __name__ == '__main__':
    print("Fixing panel visibility logic...")
    print()

    if fix_visibility():
        print()
        print("✅ Done! Refresh the page (Ctrl+Shift+R) and check.")
        print()
        print("The panel should now appear in IMAGE mode only!")
    else:
        print()
        print("❌ Failed to fix visibility logic")
