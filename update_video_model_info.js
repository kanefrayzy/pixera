// Патч для добавления функции обновления информации о модели
// Добавить этот код в класс VideoGeneration в static/js/video-generation.js

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
