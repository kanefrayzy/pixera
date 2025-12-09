#!/usr/bin/env python3
"""
Скрипт для автоматического добавления функции updateModelInfo() в video-generation.js
"""

import re

# Читаем файл
with open('static/js/video-generation.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Функция для добавления
new_function = '''
  /**
   * Обновление секции с информацией о выбранной модели
   */
  updateModelInfo() {
    const section = document.getElementById('model-info-section');
    if (!section || !this.selectedModel) {
      if (section) section.classList.add('hidden');
      return;
    }

    const model = this.selectedModel;

    // Показываем секцию
    section.classList.remove('hidden');

    // Обновляем название и описание
    const nameEl = document.getElementById('model-info-name');
    const descEl = document.getElementById('model-info-description');
    if (nameEl) nameEl.textContent = model.name || 'Без названия';
    if (descEl) descEl.textContent = model.description || 'Описание недоступно';

    // Обновляем параметры модели
    const costEl = document.getElementById('model-info-cost');
    const durationEl = document.getElementById('model-info-duration');
    const resolutionEl = document.getElementById('model-info-resolution');
    const categoryEl = document.getElementById('model-info-category');

    if (costEl) costEl.textContent = `${model.token_cost || 20} TOK`;
    if (durationEl) durationEl.textContent = `${model.max_duration || 10} сек`;

    // Разрешение - берем максимальное из доступных
    if (resolutionEl) {
      const maxRes = model.max_resolution || '1920x1080';
      resolutionEl.textContent = maxRes;
    }

    // Категория
    if (categoryEl) {
      const catMap = {
        't2v': 'Text-to-Video',
        'i2v': 'Image-to-Video',
        'anime': 'Anime'
      };
      categoryEl.textContent = catMap[model.category] || model.category_display || 'T2V';
    }

    // Обновляем список доступных функций
    const featuresList = document.getElementById('model-features-list');
    if (featuresList) {
      const features = [];

      // Основные параметры
      if (model.optional_fields) {
        const fields = model.optional_fields;

        if (fields.duration !== false) features.push({ icon: '⏱️', text: 'Длительность' });
        if (fields.resolution !== false) features.push({ icon: '📐', text: 'Разрешение' });
        if (fields.camera_movement !== false && model.supports_camera_movement) {
          features.push({ icon: '📹', text: 'Движение камеры' });
        }
        if (fields.seed !== false && model.supports_seed) {
          features.push({ icon: '🎲', text: 'Seed' });
        }
        if (fields.motion_strength !== false && model.supports_motion_strength) {
          features.push({ icon: '💫', text: 'Сила движения' });
        }
        if (fields.fps !== false && model.supports_fps) {
          features.push({ icon: '🎬', text: 'FPS' });
        }
        if (fields.guidance_scale !== false && model.supports_guidance_scale) {
          features.push({ icon: '🎯', text: 'Guidance Scale' });
        }
        if (fields.inference_steps !== false && model.supports_inference_steps) {
          features.push({ icon: '🔢', text: 'Шаги генерации' });
        }
        if (fields.quality !== false) {
          features.push({ icon: '⭐', text: 'Качество' });
        }
        if (fields.style !== false) {
          features.push({ icon: '🎨', text: 'Стиль' });
        }
        if (fields.negative_prompt !== false && model.supports_negative_prompt) {
          features.push({ icon: '🚫', text: 'Негативный промпт' });
        }
      } else {
        // Fallback если optional_fields не настроен - показываем все поддерживаемые
        features.push({ icon: '⏱️', text: 'Длительность' });
        features.push({ icon: '📐', text: 'Разрешение' });
        if (model.supports_camera_movement) features.push({ icon: '📹', text: 'Движение камеры' });
        if (model.supports_seed) features.push({ icon: '🎲', text: 'Seed' });
        if (model.supports_motion_strength) features.push({ icon: '💫', text: 'Сила движения' });
        if (model.supports_fps) features.push({ icon: '🎬', text: 'FPS' });
        if (model.supports_guidance_scale) features.push({ icon: '🎯', text: 'Guidance Scale' });
        if (model.supports_inference_steps) features.push({ icon: '🔢', text: 'Шаги' });
        if (model.supports_negative_prompt) features.push({ icon: '🚫', text: 'Негативный промпт' });
      }

      // Рендерим бейджи функций
      featuresList.innerHTML = features.map(f => `
        <span class="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-[var(--bord)]/40 text-[10px] sm:text-xs text-[var(--text)] font-medium">
          <span>${f.icon}</span>
          <span>${this.escapeHtml(f.text)}</span>
        </span>
      `).join('');
    }
  }
'''

# Проверяем, не добавлена ли уже функция
if 'updateModelInfo()' in content:
    print("✓ Функция updateModelInfo() уже существует в файле")
else:
    # Находим метод updateModelDescription и добавляем после него
    pattern = r'(updateModelDescription\(\) \{[^}]+\})'

    def replacer(match):
        return match.group(1) + new_function

    new_content = re.sub(pattern, replacer, content, count=1)

    if new_content != content:
        # Сохраняем изменения
        with open('static/js/video-generation.js', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✓ Функция updateModelInfo() успешно добавлена")
    else:
        print("✗ Не удалось найти место для вставки функции")
        print("Попробуйте добавить функцию вручную после метода updateModelDescription()")

# Теперь добавляем вызовы функции
print("\nДобавление вызовов updateModelInfo()...")

with open('static/js/video-generation.js', 'r', encoding='utf-8') as f:
    content = f.read()

changes_made = 0

# 1. После updateModelDescription() в обработчике клика
pattern1 = r'(this\.updateModelDescription\(\);)\s*\n(\s+)(\/\/ Обновляем видимость полей)'
if re.search(pattern1, content):
    content = re.sub(pattern1, r'\1\n\2this.updateModelInfo();\n\2\3', content)
    changes_made += 1
    print("✓ Добавлен вызов #1 (в обработчике клика)")

# 2. В конце updateModelSelect()
pattern2 = r'(this\.updateModelDescription\(\);)\s*\n(\s+)(\/\/ Обновляем видимость полей на основе конфигурации модели при первичном рендере)'
if re.search(pattern2, content):
    content = re.sub(pattern2, r'\1\n\2this.updateModelInfo();\n\2\3', content)
    changes_made += 1
    print("✓ Добавлен вызов #2 (в updateModelSelect)")

# 3. В обработчике change
pattern3 = r'(this\.updateModelDescription\(\);\s*\n\s+\})'
if re.search(pattern3, content):
    content = re.sub(pattern3, r'this.updateModelDescription();\n          this.updateModelInfo();\n        }', content)
    changes_made += 1
    print("✓ Добавлен вызов #3 (в обработчике change)")

if changes_made > 0:
    with open('static/js/video-generation.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✓ Успешно добавлено {changes_made} вызовов updateModelInfo()")
else:
    print("\n⚠ Вызовы не были добавлены автоматически")
    print("Добавьте вручную this.updateModelInfo(); после каждого this.updateModelDescription();")

print("\n" + "="*60)
print("Готово! Перезагрузите страницу /generate/new?type=video")
print("="*60)
