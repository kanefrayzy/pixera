"""
Integrate ImageFieldManager into templates/generate/new.html
This will enable dynamic field visibility based on selected image model configuration
"""

def integrate_field_manager():
    """Add ImageFieldManager script and integration"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add script tag for image-field-manager.js (after video-field-manager.js)
    video_field_manager_tag = '<script src="{% static \'js/video-field-manager.js\' %}"></script>'

    if video_field_manager_tag in content and 'image-field-manager.js' not in content:
        image_field_manager_tag = '<script src="{% static \'js/image-field-manager.js\' %}"></script>'
        content = content.replace(
            video_field_manager_tag,
            video_field_manager_tag + '\n    ' + image_field_manager_tag
        )
        print("✅ Added image-field-manager.js script tag")
    else:
        print("⚠️  Script tag already exists or video-field-manager.js not found")

    # 2. Find where image models are rendered and add field manager integration
    # Look for the image model card click handler
    marker = "document.querySelectorAll('.image-model-card').forEach(card=>{"

    if marker in content:
        # Find the end of the click handler
        start_pos = content.find(marker)
        # Find where we set the model data
        model_data_marker = "const model=JSON.parse(card.dataset.model||'{}');"
        model_data_pos = content.find(model_data_marker, start_pos)

        if model_data_pos > 0:
            # Find the end of this line
            line_end = content.find('\n', model_data_pos)

            # Add ImageFieldManager integration after model data is parsed
            integration_code = """

            // Update field visibility based on model configuration
            if (window.ImageFieldManager) {
              if (!window.imageFieldManager) {
                window.imageFieldManager = new window.ImageFieldManager();
              }
              window.imageFieldManager.updateFieldsForModel(model);
            }"""

            # Check if already integrated
            if 'window.imageFieldManager' not in content:
                content = content[:line_end] + integration_code + content[line_end:]
                print("✅ Added ImageFieldManager integration to image model card handler")
            else:
                print("⚠️  ImageFieldManager integration already exists")
        else:
            print("❌ Could not find model data parsing line")
    else:
        print("❌ Could not find image model card handler")

    # 3. Add initialization on page load for default model
    # Find the DOMContentLoaded or page initialization section
    init_marker = "document.addEventListener('DOMContentLoaded',"

    if init_marker in content and 'imageFieldManager' not in content[content.find(init_marker):content.find(init_marker) + 2000]:
        # Find a good place to add initialization (after mode switching logic)
        mode_switch_marker = "if(!isImage){"
        mode_switch_pos = content.find(mode_switch_marker, content.find(init_marker))

        if mode_switch_pos > 0:
            # Find the closing brace of this if block
            brace_count = 1
            pos = mode_switch_pos + len(mode_switch_marker)
            while brace_count > 0 and pos < len(content):
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1

            # Add initialization after the mode switch block
            init_code = """

      // Initialize ImageFieldManager for default image model
      if (isImage && window.ImageFieldManager) {
        const defaultImageCard = document.querySelector('.image-model-card.active');
        if (defaultImageCard && defaultImageCard.dataset.model) {
          try {
            const model = JSON.parse(defaultImageCard.dataset.model || '{}');
            if (!window.imageFieldManager) {
              window.imageFieldManager = new window.ImageFieldManager();
            }
            window.imageFieldManager.updateFieldsForModel(model);
          } catch(e) {
            console.error('Failed to initialize ImageFieldManager:', e);
          }
        }
      }"""

            content = content[:pos] + init_code + content[pos:]
            print("✅ Added ImageFieldManager initialization on page load")
        else:
            print("⚠️  Could not find mode switch block")

    # Write back
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print()
    print("✅ ImageFieldManager integration complete!")
    print()
    print("Now image fields will show/hide based on model configuration")
    print("Refresh the page and select different image models to test")

    return True


if __name__ == '__main__':
    print("Integrating ImageFieldManager...")
    print()

    if integrate_field_manager():
        print()
        print("✅ Done! Test by:")
        print("1. Go to /generate/admin/image-models/create")
        print("2. Create a model with specific optional fields")
        print("3. Go to /generate/new")
        print("4. Select that model")
        print("5. Only selected fields should be visible")
    else:
        print()
        print("❌ Integration failed")
