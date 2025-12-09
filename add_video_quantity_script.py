"""
Add video-quantity-handler.js to new.html template
"""

# Read the template
with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line with video-field-manager.js and add our script after it
old_line = '"{% static \'js/video-field-manager.js\' %}?v={{ STATIC_VERSION }}",'
new_lines = '"{% static \'js/video-field-manager.js\' %}?v={{ STATIC_VERSION }}",\n      "{% static \'js/video-quantity-handler.js\' %}?v={{ STATIC_VERSION }}",'

if old_line in content:
    content = content.replace(old_line, new_lines)

    # Write back
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Successfully added video-quantity-handler.js to new.html")
else:
    print("❌ Could not find the line to replace")
    print("Please add manually:")
    print('      "{% static \'js/video-quantity-handler.js\' %}?v={{ STATIC_VERSION }}",')
