"""
Convert video form inputs to moon sliders
Заменяет FPS, Inference Steps, Quality и Video Quantity на красивые moon-sliders
"""

# Read the template
with open('templates/generate/video_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace FPS input with moon slider
fps_old = '''      <!-- FPS -->
      <div id="fps-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]" for="video-fps">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>FPS (кадров в секунду)</span>
          </span>
        </label>
        <input type="number" id="video-fps" class="field w-full text-xs sm:text-sm h-9 sm:h-10 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all" placeholder="30" min="1" max="60">
      </div>'''

fps_new = '''      <!-- FPS -->
      <div id="fps-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>FPS (кадров в секунду)</span>
          </span>
        </label>
        <div class="moon-slider-container">
          <div class="flex items-center gap-3 sm:gap-4">
            <input
              type="range"
              id="video-fps"
              class="moon-slider flex-1"
              min="1"
              max="60"
              value="30"
              step="1"
              data-value-id="video-fps-value"
            >
            <div class="moon-slider-value">
              <span id="video-fps-value" class="moon-slider-value-number">30</span>
              <span class="moon-slider-value-unit">FPS</span>
            </div>
          </div>
        </div>
      </div>'''

# 2. Replace Inference Steps input with moon slider
steps_old = '''      <!-- Inference Steps -->
      <div id="inference-steps-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]" for="video-inference-steps">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h4l3 9 4-18 3 9h4"/>
            </svg>
            <span>Шаги генерации</span>
          </span>
        </label>
        <input type="number" id="video-inference-steps" class="field w-full text-xs sm:text-sm h-9 sm:h-10 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all" placeholder="50" min="10" max="100">
      </div>'''

steps_new = '''      <!-- Inference Steps -->
      <div id="inference-steps-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h4l3 9 4-18 3 9h4"/>
            </svg>
            <span>Шаги генерации</span>
          </span>
        </label>
        <div class="moon-slider-container">
          <div class="flex items-center gap-3 sm:gap-4">
            <input
              type="range"
              id="video-inference-steps"
              class="moon-slider flex-1"
              min="10"
              max="100"
              value="50"
              step="1"
              data-value-id="video-inference-steps-value"
            >
            <div class="moon-slider-value">
              <span id="video-inference-steps-value" class="moon-slider-value-number">50</span>
              <span class="moon-slider-value-unit">шагов</span>
            </div>
          </div>
        </div>
      </div>'''

# 3. Replace Quality select with moon slider
quality_old = '''      <!-- Quality -->
      <div id="quality-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]" for="video-quality">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
            <span>Качество</span>
          </span>
        </label>
        <select id="video-quality" class="field w-full text-xs sm:text-sm h-9 sm:h-10 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all appearance-none">
          <option value="">По умолчанию</option>
          <option value="low">Низкое</option>
          <option value="medium">Среднее</option>
          <option value="high">Высокое</option>
          <option value="ultra">Ультра</option>
        </select>
      </div>'''

quality_new = '''      <!-- Quality -->
      <div id="quality-param" class="space-y-1.5" style="display: none;">
        <label class="block text-xs sm:text-sm font-medium text-[var(--text)]">
          <span class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-primary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
            <span>Качество</span>
          </span>
        </label>
        <div class="moon-slider-container">
          <div class="flex items-center gap-3 sm:gap-4">
            <input
              type="range"
              id="video-quality"
              class="moon-slider flex-1"
              min="0"
              max="4"
              value="2"
              step="1"
              data-value-id="video-quality-value"
              data-labels='["По умолчанию", "Низкое", "Среднее", "Высокое", "Ультра"]'
            >
            <div class="moon-slider-value">
              <span id="video-quality-value" class="moon-slider-value-number">Среднее</span>
            </div>
          </div>
        </div>
        <input type="hidden" id="video-quality-hidden" value="medium">
      </div>'''

# 4. Update Video Quantity to use moon-slider class
quantity_old = '''    <!-- Video Quantity Selector -->
    <div id="video-quantity-container" class="sm:col-span-2 space-y-1.5" style="display: none;">
      <label class="block text-xs sm:text-sm font-medium mb-1.5">
        <span class="flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5 flex-shrink-0 text-primary dark:text-primary/90" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
          <span class="text-xs sm:text-sm">Количество видео</span>
        </span>
      </label>
      <div class="flex items-center gap-3 sm:gap-4">
        <input
          type="range"
          id="video-quantity"
          name="number_videos"
          min="1"
          max="4"
          value="1"
          class="slider-thumb flex-1"
        >
        <div class="flex items-center gap-2 px-3 py-1.5 sm:py-2 rounded-lg bg-[var(--bord)]/60 min-w-[70px] justify-center">
          <span id="video-quantity-value" class="text-base sm:text-lg font-bold text-primary tabular-nums">1</span>
          <span class="text-xs sm:text-sm text-[var(--muted)]">видео</span>
        </div>
      </div>
      <p class="text-[10px] sm:text-xs text-[var(--muted)] mt-1">
        💡 Цена умножается на количество видео
      </p>
    </div>'''

quantity_new = '''    <!-- Video Quantity Selector -->
    <div id="video-quantity-container" class="sm:col-span-2 space-y-1.5" style="display: none;">
      <label class="block text-xs sm:text-sm font-medium mb-1.5">
        <span class="flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5 flex-shrink-0 text-primary dark:text-primary/90" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
          <span class="text-xs sm:text-sm">Количество видео</span>
        </span>
      </label>
      <div class="moon-slider-container">
        <div class="flex items-center gap-3 sm:gap-4">
          <input
            type="range"
            id="video-quantity"
            name="number_videos"
            class="moon-slider flex-1"
            min="1"
            max="4"
            value="1"
            step="1"
            data-value-id="video-quantity-value"
          >
          <div class="moon-slider-value">
            <span id="video-quantity-value" class="moon-slider-value-number">1</span>
            <span class="moon-slider-value-unit">видео</span>
          </div>
        </div>
        <p class="text-[10px] sm:text-xs text-[var(--muted)] mt-1">
          💡 Цена умножается на количество видео
        </p>
      </div>
    </div>'''

# Apply replacements
content = content.replace(fps_old, fps_new)
content = content.replace(steps_old, steps_new)
content = content.replace(quality_old, quality_new)
content = content.replace(quantity_old, quantity_new)

# Write back
with open('templates/generate/video_form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Successfully converted all inputs to moon sliders!")
print("   - FPS: number input → moon slider (1-60)")
print("   - Inference Steps: number input → moon slider (10-100)")
print("   - Quality: select → moon slider (0-4 with labels)")
print("   - Video Quantity: updated to moon-slider class")
