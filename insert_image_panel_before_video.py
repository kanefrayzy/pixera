"""
Insert image admin panel before video admin panel
"""

def insert_panel():
    """Insert the image admin panel before the video panel"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the video admin panel
    video_panel_marker = '<!-- Admin Panel for Video Models'
    video_panel_pos = content.find(video_panel_marker)

    if video_panel_pos == -1:
        print("❌ Video admin panel not found")
        return False

    print(f"✅ Video panel found at position: {video_panel_pos}")

    # Check if image panel already exists
    image_panel_marker = '<!-- Admin Panel for Image Models'
    if image_panel_marker in content:
        print("⚠️  Image panel already exists, removing old one first...")
        # Find and remove old panel
        start = content.find(image_panel_marker)
        end = content.find('<!-- End Admin Panel for Image Models')
        if end != -1:
            end = content.find('-->', end) + 3
            content = content[:start] + content[end:]
            print("✅ Old panel removed")

    # Create the image admin panel HTML
    panel_html = '''    <!-- Admin Panel for Image Models (только для админов) -->
    {% if request.user.is_staff %}
    <div class="mt-6 p-4 rounded-xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10" id="image-models-admin-panel">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
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

    # Insert before video panel
    video_panel_pos = content.find(video_panel_marker)  # Re-find after potential removal
    new_content = content[:video_panel_pos] + panel_html + content[video_panel_pos:]

    # Write back
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Image admin panel inserted successfully!")
    print(f"   Inserted before video panel at position: {video_panel_pos}")
    print()
    print("Panel includes:")
    print("  ✅ Staff check: {% if request.user.is_staff %}")
    print("  ✅ Panel ID: image-models-admin-panel")
    print("  ✅ Link to create page")
    print("  ✅ Proper styling")
    print()
    return True


if __name__ == '__main__':
    print("Inserting image admin panel...")
    print()

    if insert_panel():
        print("✅ Done! Now refresh the page (Ctrl+Shift+R)")
        print()
        print("The panel should appear:")
        print("  - Before the video models panel")
        print("  - Only for admin users (is_staff=True)")
        print("  - Only in image mode (controlled by JavaScript)")
    else:
        print("❌ Failed to insert panel")
