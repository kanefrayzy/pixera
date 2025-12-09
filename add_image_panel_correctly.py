"""
Add image admin panel correctly to templates/generate/new.html
"""

def add_panel():
    """Add the image admin panel in the correct location"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the video admin panel to use as reference
    video_panel_marker = '<!-- Admin Panel for Video Models'
    video_panel_pos = content.find(video_panel_marker)

    if video_panel_pos == -1:
        print("❌ Video admin panel not found - cannot determine insertion point")
        return False

    # The image panel should be BEFORE the video panel
    # Find a good insertion point - after the mode toggle buttons
    mode_toggle_marker = 'id="mode-toggle"'
    mode_toggle_pos = content.find(mode_toggle_marker)

    if mode_toggle_pos == -1:
        print("❌ Mode toggle not found")
        return False

    # Find the end of the mode toggle section (look for closing div)
    # We'll insert after the mode toggle container
    insertion_point = content.find('</div>', mode_toggle_pos)
    if insertion_point == -1:
        print("❌ Could not find insertion point")
        return False

    insertion_point += len('</div>') + 1  # After the closing div and newline

    # Create the image admin panel HTML
    panel_html = '''
    <!-- Admin Panel for Image Models (только для админов) -->
    {% if request.user.is_staff %}
    <div class="mt-6 p-4 rounded-xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10" id="image-models-admin-panel">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            Управление моделями изображений
          </h3>
        </div>
        <a href="{% url 'generate:image_model_create' %}"
           class="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
          </svg>
          Добавить модель
        </a>
      </div>

      <div class="text-sm text-gray-600 dark:text-gray-400">
        <p>Здесь вы можете управлять моделями для генерации изображений</p>
      </div>
    </div>
    {% endif %}
    <!-- End Admin Panel for Image Models -->
'''

    # Insert the panel
    new_content = content[:insertion_point] + panel_html + content[insertion_point:]

    # Write back
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Image admin panel added successfully!")
    print(f"   Inserted at position: {insertion_point}")
    print()
    print("Panel includes:")
    print("  ✅ Staff check: {% if request.user.is_staff %}")
    print("  ✅ Panel ID: image-models-admin-panel")
    print("  ✅ Link to create page")
    print("  ✅ Proper styling")
    print()
    return True


if __name__ == '__main__':
    print("Adding image admin panel...")
    print()

    if add_panel():
        print("✅ Done! Refresh the page and check.")
        print()
        print("The panel should now appear:")
        print("  - After the mode toggle buttons")
        print("  - Only for admin users (is_staff=True)")
        print("  - Only in image mode")
    else:
        print("❌ Failed to add panel")
