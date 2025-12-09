"""
Script to add Image Models Admin Panel to generate/new.html template
"""

def add_admin_panel():
    """Add admin panel for image models to the generation page"""

    template_path = 'templates/generate/new.html'

    # Read the template
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already added
    if 'image-models-admin-panel' in content:
        print("⚠️  Admin panel already exists in template")
        return

    # Find the video admin panel section
    video_panel_start = content.find('<!-- Admin Panel for Video Models (только для админов) -->')

    if video_panel_start == -1:
        print("❌ Could not find video admin panel marker")
        return

    # Find the end of video admin panel
    video_panel_end = content.find('{% endif %}', video_panel_start)
    if video_panel_end == -1:
        print("❌ Could not find end of video admin panel")
        return

    # Move to after the closing tag
    video_panel_end = content.find('\n', video_panel_end) + 1

    # Image admin panel HTML
    image_panel = '''
    <!-- Admin Panel for Image Models (только для админов) -->
    {% if request.user.is_staff %}
    <div class="mt-6 p-4 rounded-xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10" id="image-models-admin-panel" style="{% if request.GET.type == 'video' %}display:none{% endif %}">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
          </div>
          <div>
            <h3 class="font-bold text-base">Управление моделями изображений</h3>
            <p class="text-xs text-[var(--muted)]">Настройка параметров моделей Runware</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <a href="{% url 'generate:image_models_list' %}" class="group flex items-center gap-3 p-4 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary/50 hover:bg-primary/5 transition-all">
          <div class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
            <svg class="w-5 h-5 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm">Список моделей</div>
            <div class="text-xs text-[var(--muted)]">Просмотр всех моделей</div>
          </div>
          <svg class="w-5 h-5 text-[var(--muted)] group-hover:text-primary transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </a>

        <a href="{% url 'generate:image_model_create' %}" class="group flex items-center gap-3 p-4 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary/50 hover:bg-primary/5 transition-all">
          <div class="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
            <svg class="w-5 h-5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm">Добавить модель</div>
            <div class="text-xs text-[var(--muted)]">Создать новую модель</div>
          </div>
          <svg class="w-5 h-5 text-[var(--muted)] group-hover:text-primary transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </a>

        <a href="/admin/generate/imagemodelconfiguration/" target="_blank" class="group flex items-center gap-3 p-4 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary/50 hover:bg-primary/5 transition-all">
          <div class="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
            <svg class="w-5 h-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm">Django Admin</div>
            <div class="text-xs text-[var(--muted)]">Расширенные настройки</div>
          </div>
          <svg class="w-5 h-5 text-[var(--muted)] group-hover:text-primary transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </a>
      </div>
    </div>
    {% endif %}
'''

    # Insert the image panel after video panel
    new_content = content[:video_panel_end] + image_panel + content[video_panel_end:]

    # Now update the JavaScript to handle panel visibility
    # Find the switchMode function
    switch_mode_marker = "const imageAdminPanel=document.getElementById('image-models-admin-panel');"

    if switch_mode_marker not in new_content:
        # Find where to add the panel visibility code
        admin_panel_marker = "const adminPanel=document.getElementById('video-models-admin-panel');"
        admin_panel_pos = new_content.find(admin_panel_marker)

        if admin_panel_pos != -1:
            # Find the end of that line
            line_end = new_content.find('\n', admin_panel_pos)

            # Add image admin panel handling
            image_panel_code = "\n      const imageAdminPanel=document.getElementById('image-models-admin-panel');"
            new_content = new_content[:line_end] + image_panel_code + new_content[line_end:]

            # Now find where adminPanel visibility is set and add imageAdminPanel
            admin_display_marker = "if(adminPanel)adminPanel.style.display=isImage?'none':'block';"
            admin_display_pos = new_content.find(admin_display_marker)

            if admin_display_pos != -1:
                line_end = new_content.find('\n', admin_display_pos)
                image_display_code = "\n      if(imageAdminPanel)imageAdminPanel.style.display=isImage?'block':'none';"
                new_content = new_content[:line_end] + image_display_code + new_content[line_end:]

    # Write the updated template
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Successfully added Image Models Admin Panel to template")
    print()
    print("Added features:")
    print("  - Admin panel for image models (visible only for staff)")
    print("  - Link to image models list")
    print("  - Link to create new image model")
    print("  - Link to Django admin")
    print("  - Auto-hide when switching to video mode")
    print("  - Auto-show when switching to image mode")


if __name__ == '__main__':
    print("Adding Image Models Admin Panel to generation page...")
    print()

    try:
        add_admin_panel()
        print()
        print("✅ Done! The admin panel has been added to templates/generate/new.html")
        print()
        print("Next steps:")
        print("1. Refresh the page at /generate/new")
        print("2. Login as admin")
        print("3. You should see the Image Models admin panel")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
