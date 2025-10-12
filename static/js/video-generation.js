/**
 * Модуль генерации видео
 * Управляет формой генерации видео, отправкой запросов и отображением результатов
 */

class VideoGeneration {
  constructor() {
    this.currentMode = 't2v'; // t2v или i2v
    this.selectedModel = null;
    this.models = [];
    this.sourceImage = null;
    this.providerFields = {}; // Хранилище значений специфичных полей

    this.init();
  }

  async init() {
    await this.loadModels();
    this.setupEventListeners();
    this.updateModelSelect();
  }

  /**
   * Загрузка списка моделей видео
   */
  async loadModels() {
    try {
      const response = await fetch('/generate/api/video/models');
      const data = await response.json();

      if (data.success) {
        this.models = data.models;
        console.log('Загружено моделей видео:', this.models.length);
      } else {
        console.error('Ошибка загрузки моделей:', data.error);
        this.showError('Не удалось загрузить модели видео');
      }
    } catch (error) {
      console.error('Ошибка при загрузке моделей:', error);
      this.showError('Ошибка подключения к серверу');
    }
  }

  /**
   * Обновление списка моделей в select
   */
  updateModelSelect() {
    const select = document.getElementById('video-model');
    if (!select) return;

    // Фильтруем модели по текущему режиму
    let filteredModels = this.models;
    if (this.currentMode === 'i2v') {
      // Показываем I2V-модели, а также ByteDance 1.1 (bytedance:1@1), доступную в обоих режимах
      filteredModels = this.models.filter(m => m.category === 'i2v' || m.model_id === 'bytedance:1@1');
    } else {
      filteredModels = this.models.filter(m => m.category === 't2v' || m.category === 'anime');
    }

    if (filteredModels.length === 0) {
      select.innerHTML = '<option value="">Нет доступных моделей</option>';
      return;
    }

    // Заполняем select с улучшенным форматированием
    select.innerHTML = filteredModels.map(model => {
      const name = model.name || 'Без названия';
      const cost = model.token_cost || 20;
      const duration = model.max_duration || 8;

      return `<option value="${model.id}"
                data-cost="${cost}"
                data-max-duration="${duration}"
                data-model-id="${model.model_id}"
                title="${model.description || name}">
        ${name} · ${cost} TOK · до ${duration} сек
      </option>`;
    }).join('');

    // Выбираем первую модель
    if (filteredModels.length > 0) {
      this.selectedModel = filteredModels[0];
      this.updateCost();
      this.updateDurationLimit();
      this.updateProviderFields();
    }
  }

  /**
   * Получить провайдера из model_id
   */
  getProvider(modelId) {
    if (!modelId || typeof modelId !== 'string') return '';
    return modelId.split(':')[0].toLowerCase();
  }

  /**
   * Обновление специфичных полей провайдера
   */
  updateProviderFields() {
    if (!this.selectedModel) {
      this.hideProviderFields();
      return;
    }

    const provider = this.getProvider(this.selectedModel.model_id);
    const container = document.getElementById('provider-fields-container');
    const wrapper = document.getElementById('provider-specific-fields');

    if (!container || !wrapper) return;

    // Очищаем контейнер
    container.innerHTML = '';

    // Определяем поля для каждого провайдера
    const fields = this.getProviderFieldsConfig(provider);

    if (fields.length === 0) {
      this.hideProviderFields();
      return;
    }

    // Создаем поля
    fields.forEach(field => {
      const fieldHtml = this.createFieldHTML(field);
      container.insertAdjacentHTML('beforeend', fieldHtml);
    });

    // Показываем секцию
    wrapper.classList.remove('hidden');

    // Устанавливаем обработчики событий для новых полей
    this.setupProviderFieldListeners();
  }

  /**
   * Скрыть специфичные поля провайдера
   */
  hideProviderFields() {
    const wrapper = document.getElementById('provider-specific-fields');
    if (wrapper) {
      wrapper.classList.add('hidden');
    }
  }

  /**
   * Получить конфигурацию полей для провайдера
   */
  getProviderFieldsConfig(provider) {
    const configs = {
      'bytedance': [
        {
          type: 'checkbox',
          id: 'camera-fixed',
          name: 'camera_fixed',
          label: 'Фиксированная камера',
          description: 'Камера остается неподвижной',
          default: false
        }
      ],
      'google': [
        {
          type: 'checkbox',
          id: 'enhance-prompt',
          name: 'enhance_prompt',
          label: 'Улучшить промпт',
          description: 'Автоматическое улучшение описания',
          default: true
        },
        {
          type: 'checkbox',
          id: 'generate-audio',
          name: 'generate_audio',
          label: 'Генерировать аудио',
          description: 'Добавить звук к видео (только Veo 3)',
          default: false
        }
      ],
      'minimax': [
        {
          type: 'checkbox',
          id: 'prompt-optimizer',
          name: 'prompt_optimizer',
          label: 'Оптимизировать промпт',
          description: 'Улучшить качество описания',
          default: false
        }
      ],
      'pixverse': [
        {
          type: 'select',
          id: 'pixverse-style',
          name: 'style',
          label: 'Стиль',
          description: 'Художественный стиль видео',
          options: [
            { value: '', label: 'Без стиля' },
            { value: 'anime', label: 'Anime' },
            { value: '3d_animation', label: '3D Animation' },
            { value: 'clay', label: 'Clay' },
            { value: 'comic', label: 'Comic' },
            { value: 'cyberpunk', label: 'Cyberpunk' }
          ]
        },
        {
          type: 'select',
          id: 'pixverse-effect',
          name: 'effect',
          label: 'Эффект',
          description: 'Вирусный эффект (нельзя с движением камеры)',
          options: [
            { value: '', label: 'Без эффекта' },
            { value: 'jiggle jiggle', label: 'Jiggle Jiggle' },
            { value: 'skeleton dance', label: 'Skeleton Dance' },
            { value: 'kungfu club', label: 'Kungfu Club' },
            { value: 'boom drop', label: 'Boom Drop' },
            { value: 'eye zoom challenge', label: 'Eye Zoom Challenge' }
          ]
        },
        {
          type: 'select',
          id: 'pixverse-camera',
          name: 'camera_movement',
          label: 'Движение камеры',
          description: 'Кинематографическое движение (нельзя с эффектом)',
          options: [
            { value: '', label: 'Без движения' },
            { value: 'zoom_in', label: 'Zoom In' },
            { value: 'zoom_out', label: 'Zoom Out' },
            { value: 'pan_left', label: 'Pan Left' },
            { value: 'pan_right', label: 'Pan Right' },
            { value: 'auto_camera', label: 'Auto Camera' }
          ]
        },
        {
          type: 'select',
          id: 'motion-mode',
          name: 'motion_mode',
          label: 'Интенсивность движения',
          options: [
            { value: 'normal', label: 'Нормальная' },
            { value: 'fast', label: 'Быстрая' }
          ],
          default: 'normal'
        }
      ],
      'vidu': [
        {
          type: 'select',
          id: 'movement-amplitude',
          name: 'movement_amplitude',
          label: 'Амплитуда движения',
          options: [
            { value: 'auto', label: 'Авто' },
            { value: 'small', label: 'Малая' },
            { value: 'medium', label: 'Средняя' },
            { value: 'large', label: 'Большая' }
          ],
          default: 'auto'
        },
        {
          type: 'checkbox',
          id: 'vidu-bgm',
          name: 'bgm',
          label: 'Фоновая музыка',
          description: 'Добавить музыку (только для 4 сек)',
          default: false
        },
        {
          type: 'select',
          id: 'vidu-style',
          name: 'style',
          label: 'Стиль',
          description: 'Только для text-to-video',
          options: [
            { value: 'general', label: 'Общий' },
            { value: 'anime', label: 'Anime' }
          ],
          default: 'general'
        }
      ]
    };

    return configs[provider] || [];
  }

  /**
   * Создать HTML для поля
   */
  createFieldHTML(field) {
    if (field.type === 'checkbox') {
      return `
        <div class="flex items-start gap-3 p-3 rounded-lg bg-[var(--bord)]/30 hover:bg-[var(--bord)]/50 transition-colors">
          <input type="checkbox"
                 id="${field.id}"
                 name="${field.name}"
                 ${field.default ? 'checked' : ''}
                 class="mt-1 w-4 h-4 rounded border-[var(--bord)] bg-[var(--bg)] text-primary focus:ring-2 focus:ring-primary/20">
          <div class="flex-1">
            <label for="${field.id}" class="block text-sm font-medium cursor-pointer">
              ${field.label}
            </label>
            ${field.description ? `
              <p class="text-xs text-[var(--muted)] mt-0.5">${field.description}</p>
            ` : ''}
          </div>
        </div>
      `;
    } else if (field.type === 'select') {
      return `
        <div>
          <label class="block text-sm font-medium mb-2" for="${field.id}">
            ${field.label}
          </label>
          ${field.description ? `
            <p class="text-xs text-[var(--muted)] mb-2">${field.description}</p>
          ` : ''}
          <select id="${field.id}" name="${field.name}" class="field w-full">
            ${field.options.map(opt => `
              <option value="${opt.value}" ${field.default === opt.value ? 'selected' : ''}>
                ${opt.label}
              </option>
            `).join('')}
          </select>
        </div>
      `;
    }
    return '';
  }

  /**
   * Настройка обработчиков для специфичных полей провайдера
   */
  setupProviderFieldListeners() {
    const container = document.getElementById('provider-fields-container');
    if (!container) return;

    const provider = this.getProvider(this.selectedModel?.model_id);

    // Для PixVerse: effect и cameraMovement взаимоисключающие
    if (provider === 'pixverse') {
      const effectSelect = document.getElementById('pixverse-effect');
      const cameraSelect = document.getElementById('pixverse-camera');

      if (effectSelect && cameraSelect) {
        effectSelect.addEventListener('change', (e) => {
          if (e.target.value) {
            cameraSelect.value = '';
            cameraSelect.disabled = true;
            cameraSelect.classList.add('opacity-50', 'cursor-not-allowed');
          } else {
            cameraSelect.disabled = false;
            cameraSelect.classList.remove('opacity-50', 'cursor-not-allowed');
          }
        });

        cameraSelect.addEventListener('change', (e) => {
          if (e.target.value) {
            effectSelect.value = '';
            effectSelect.disabled = true;
            effectSelect.classList.add('opacity-50', 'cursor-not-allowed');
          } else {
            effectSelect.disabled = false;
            effectSelect.classList.remove('opacity-50', 'cursor-not-allowed');
          }
        });
      }
    }

    // Для Vidu: BGM автоматически устанавливает duration=4
    if (provider === 'vidu' && this.selectedModel.model_id === 'vidu:1@5') {
      const bgmCheckbox = document.getElementById('vidu-bgm');
      if (bgmCheckbox) {
        bgmCheckbox.addEventListener('change', () => {
          this.updateDurationLimit();
        });
      }
    }
  }

  /**
   * Обновление отображения стоимости
   */
  updateCost() {
    const costDisplay = document.getElementById('video-cost-display');
    if (!costDisplay || !this.selectedModel) return;

    const cost = this.selectedModel.token_cost || 20;
    costDisplay.innerHTML = `
      ${cost}
      <svg class="w-4 h-4 text-primary" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" opacity="0.15"></circle>
        <circle cx="12" cy="12" r="6" opacity="0.35"></circle>
        <path d="M12 9.25a2.75 2.75 0 110 5.5 2.75 2.75 0 010-5.5z" />
      </svg>
    `;
  }

  /**
   * Обновление лимита длительности с учетом специфики модели
   */
  updateDurationLimit() {
    const durationSlider = document.getElementById('video-duration');
    const durationValue = document.getElementById('duration-value');
    if (!durationSlider || !this.selectedModel) return;

    const provider = this.getProvider(this.selectedModel.model_id);
    const modelId = this.selectedModel.model_id;

    // Специальная логика для каждой модели
    if (modelId === 'google:3@0') {
      // Google Veo 3.0 - РОВНО 8 секунд
      durationSlider.value = 8;
      durationSlider.min = 8;
      durationSlider.max = 8;
      durationSlider.disabled = true;
      durationSlider.classList.add('opacity-50', 'cursor-not-allowed');
      if (durationValue) durationValue.textContent = '8 (фиксировано)';
    } else if (modelId === 'vidu:1@5') {
      // Vidu 1.5 - 4 секунды для BGM
      const bgmCheckbox = document.getElementById('vidu-bgm');
      if (bgmCheckbox?.checked) {
        durationSlider.value = 4;
        durationSlider.min = 4;
        durationSlider.max = 4;
        durationSlider.disabled = true;
        durationSlider.classList.add('opacity-50', 'cursor-not-allowed');
        if (durationValue) durationValue.textContent = '4 (для BGM)';
      } else {
        durationSlider.min = 2;
        durationSlider.max = 8;
        durationSlider.disabled = false;
        durationSlider.classList.remove('opacity-50', 'cursor-not-allowed');
        if (durationValue) durationValue.textContent = durationSlider.value;
      }
    } else if (modelId === 'vidu:1@1') {
      // Vidu Q1 I2V - РОВНО 5 секунд
      durationSlider.value = 5;
      durationSlider.min = 5;
      durationSlider.max = 5;
      durationSlider.disabled = true;
      durationSlider.classList.add('opacity-50', 'cursor-not-allowed');
      if (durationValue) durationValue.textContent = '5 (фиксировано)';
    } else {
      // Стандартная логика
      const maxDuration = this.selectedModel.max_duration || 10;
      durationSlider.min = 2;
      durationSlider.max = maxDuration;
      durationSlider.disabled = false;
      durationSlider.classList.remove('opacity-50', 'cursor-not-allowed');

      if (parseInt(durationSlider.value) > maxDuration) {
        durationSlider.value = maxDuration;
      }
      if (durationValue) durationValue.textContent = durationSlider.value;
    }
  }

  /**
   * Настройка обработчиков событий
   */
  setupEventListeners() {
    // Переключатель T2V / I2V
    document.querySelectorAll('.video-source-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const source = e.target.dataset.source;
        if (source) this.switchMode(source);
      });
    });

    // Выбор модели
    const modelSelect = document.getElementById('video-model');
    if (modelSelect) {
      modelSelect.addEventListener('change', (e) => {
        const modelId = parseInt(e.target.value);
        this.selectedModel = this.models.find(m => m.id === modelId);
        if (this.selectedModel) {
          this.updateCost();
          this.updateDurationLimit();
          this.updateProviderFields();
        }
      });
    }

    // Слайдер длительности
    const durationSlider = document.getElementById('video-duration');
    const durationValue = document.getElementById('duration-value');
    if (durationSlider && durationValue) {
      durationSlider.addEventListener('input', (e) => {
        durationValue.textContent = e.target.value;
      });
    }

    // Слайдер силы движения
    const motionSlider = document.getElementById('video-motion-strength');
    const motionValue = document.getElementById('motion-value');
    if (motionSlider && motionValue) {
      motionSlider.addEventListener('input', (e) => {
        motionValue.textContent = e.target.value;
      });
    }

    // Кнопки соотношения сторон
    document.querySelectorAll('.aspect-ratio-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.aspect-ratio-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
      });
    });

    // Загрузка изображения для I2V
    this.setupImageUpload();

    // Кнопка генерации
    const generateBtn = document.getElementById('generate-video-btn');
    if (generateBtn) {
      generateBtn.addEventListener('click', () => this.generateVideo());
    }
  }

  /**
   * Переключение режима T2V / I2V
   */
  switchMode(mode) {
    this.currentMode = mode;

    // Обновляем активные табы
    document.querySelectorAll('.video-source-tab').forEach(tab => {
      if (tab.dataset.source === mode) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    // Показываем/скрываем I2V поля
    const i2vFields = document.getElementById('i2v-fields');
    if (i2vFields) {
      i2vFields.style.display = mode === 'i2v' ? 'block' : 'none';
    }

    // Обновляем список моделей
    this.updateModelSelect();
  }

  /**
   * Настройка загрузки изображения
   */
  setupImageUpload() {
    const uploadArea = document.getElementById('video-upload-area');
    const fileInput = document.getElementById('video-source-image');
    const preview = document.getElementById('video-image-preview');
    const removeBtn = document.getElementById('remove-video-image');

    if (!uploadArea || !fileInput) return;

    // Клик по области
    uploadArea.addEventListener('click', () => fileInput.click());

    // Выбор файла
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) this.handleImageFile(file);
    });

    // Drag & Drop
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');

      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.handleImageFile(file);
      }
    });

    // Удаление изображения
    if (removeBtn) {
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.sourceImage = null;
        fileInput.value = '';
        if (preview) preview.classList.add('hidden');
        uploadArea.style.display = 'block';
      });
    }
  }

  /**
   * Обработка загруженного изображения
   */
  handleImageFile(file) {
    // Проверка размера (макс 10MB)
    if (file.size > 10 * 1024 * 1024) {
      this.showError('Размер файла не должен превышать 10MB');
      return;
    }

    // Проверка типа
    if (!file.type.startsWith('image/')) {
      this.showError('Пожалуйста, выберите изображение');
      return;
    }

    this.sourceImage = file;

    // Показываем превью
    const reader = new FileReader();
    reader.onload = (e) => {
      const preview = document.getElementById('video-image-preview');
      const img = preview?.querySelector('img');
      const uploadArea = document.getElementById('video-upload-area');

      if (img && preview && uploadArea) {
        img.src = e.target.result;
        preview.classList.remove('hidden');
        uploadArea.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  }

  /**
   * Собрать значения специфичных полей провайдера
   */
  collectProviderFields() {
    const provider = this.getProvider(this.selectedModel?.model_id);
    const fields = this.getProviderFieldsConfig(provider);
    const values = {};

    fields.forEach(field => {
      const element = document.getElementById(field.id);
      if (!element) return;

      if (field.type === 'checkbox') {
        // Добавляем только если чекбокс отмечен (true)
        if (element.checked) {
          values[field.name] = true;
        }
      } else if (field.type === 'select') {
        const value = element.value;
        if (value) {  // Добавляем только если значение не пустое
          values[field.name] = value;
        }
      }
    });

    return values;
  }

  /**
   * Генерация видео
   */
  async generateVideo() {
    const prompt = document.getElementById('video-prompt')?.value.trim();

    if (!prompt) {
      this.showError('Пожалуйста, введите описание сцены');
      return;
    }

    if (!this.selectedModel) {
      this.showError('Пожалуйста, выберите модель');
      return;
    }

    // Для I2V проверяем наличие изображения
    if (this.currentMode === 'i2v' && !this.sourceImage) {
      this.showError('Пожалуйста, загрузите исходное изображение');
      return;
    }

    // Собираем параметры
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('video_model_id', this.selectedModel.id);
    formData.append('generation_mode', this.currentMode);

    const duration = document.getElementById('video-duration')?.value || 5;
    formData.append('duration', duration);

    const activeRatioBtn = document.querySelector('.aspect-ratio-btn.active');
    const aspectRatio = activeRatioBtn?.dataset.ratio || '16:9';
    formData.append('aspect_ratio', aspectRatio);

    const resolution = document.getElementById('video-resolution')?.value || '1920x1080';
    formData.append('resolution', resolution);

    const camera = document.getElementById('video-camera')?.value;
    if (camera) formData.append('camera_movement', camera);

    const seed = document.getElementById('video-seed')?.value.trim();
    if (seed) formData.append('seed', seed);

    // Добавляем специфичные поля провайдера
    const providerFields = this.collectProviderFields();
    if (Object.keys(providerFields).length > 0) {
      formData.append('provider_fields', JSON.stringify(providerFields));
    }

    // Для I2V добавляем изображение и силу движения
    if (this.currentMode === 'i2v') {
      formData.append('source_image', this.sourceImage);
      const motionStrength = document.getElementById('video-motion-strength')?.value || 45;
      formData.append('motion_strength', motionStrength);
    }

    // Показываем лоадер
    this.showLoader('Отправка запроса...');

    try {
      const response = await fetch('/generate/api/video/submit', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken()
        }
      });

      const data = await response.json();

      if (data.success) {
        console.log('Видео задача отправлена:', data.job_id);

        // Проверяем - может видео уже готово (instant результат)
        if (data.status === 'done' && data.video_url) {
          console.log('Видео готово моментально!');
          this.hideLoader();
          this.showVideoResult(data.video_url, data.job_id, data.gallery_id);
        } else {
          // Начинаем polling - Celery задача автоматически получит результат
          this.updateLoader('Генерация видео...', 5);
          this.pollVideoStatus(data.job_id);
        }
      } else {
        this.hideLoader();
        this.showError(data.error || 'Ошибка при генерации видео');
      }
    } catch (error) {
      this.hideLoader();
      console.error('Ошибка при отправке запроса:', error);
      this.showError('Ошибка при отправке запроса. Попробуйте позже.');
    }
  }

  /**
   * Polling статуса генерации
   */
  async pollVideoStatus(jobId, attempts = 0) {
    const maxAttempts = 120; // 2 минуты (каждую секунду)

    if (attempts >= maxAttempts) {
      // Продолжаем проверять еще дольше, но реже
      this.updateLoader('Почти готово...', 98);
      setTimeout(() => this.pollVideoStatus(jobId, attempts + 1), 2000);
      return;
    }

    try {
      const response = await fetch(`/generate/api/video/status/${jobId}`);
      const data = await response.json();

      if (data.status === 'done' && data.video_url) {
        this.hideLoader();
        this.showVideoResult(data.video_url, jobId, data.gallery_id);

        // Сохраняем в IndexedDB кеш
        if (window.videoCache && data.cached_until) {
          await window.videoCache.store(jobId, data.video_url, data.cached_until);
        }
      } else if (data.status === 'failed') {
        this.hideLoader();
        this.showError(data.error || 'Ошибка при генерации видео');
      } else {
        // Обновляем прогресс (если сервер дал прогресс — используем его)
        const p = (data && typeof data.progress === 'number')
          ? Math.min(98, data.progress)
          : Math.min(98, (attempts / maxAttempts) * 100);
        this.updateLoader('Генерация видео...', p);

        // Продолжаем polling чаще (примерно раз в секунду)
        setTimeout(() => this.pollVideoStatus(jobId, attempts + 1), 1000);
      }
    } catch (error) {
      console.error('Ошибка при проверке статуса:', error);
      // Продолжаем попытки при ошибке сети
      setTimeout(() => this.pollVideoStatus(jobId, attempts + 1), 1000);
    }
  }

  /**
   * Отображение результата (как для фото)
   */
  showVideoResult(videoUrl, jobId, galleryId) {
    // Создаем модальное окно в стиле результата фото
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 video-result-modal';
    modal.innerHTML = `
      <div class="modal-content bg-[var(--bg-card)] rounded-2xl max-w-4xl w-full p-6 border border-[var(--bord)] shadow-2xl">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-xl font-bold">Видео готово!</h3>
          <button class="close-video-modal w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--bord)] transition-colors" aria-label="Закрыть">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="video-preview-container aspect-video bg-black rounded-lg overflow-hidden mb-4">
          <video controls autoplay loop class="w-full h-full">
            <source src="${videoUrl}" type="video/mp4">
            Ваш браузер не поддерживает видео.
          </video>
        </div>

        <div class="flex flex-col sm:flex-row gap-3">
          <a href="${videoUrl}" download class="video-action-btn primary flex-1">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Скачать видео
          </a>
          ${galleryId ? `
          <a href="/gallery/${galleryId}/" class="video-action-btn secondary flex-1">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            Открыть в галерее
          </a>
          ` : ''}
          <button class="video-action-btn secondary flex-1 close-video-modal">
            Закрыть
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    // Анимация появления
    requestAnimationFrame(() => {
      modal.classList.add('active');
    });

    // Закрытие модального окна
    const closeModal = () => {
      modal.classList.remove('active');
      setTimeout(() => {
        modal.remove();
        document.body.style.overflow = '';
      }, 300);
    };

    modal.querySelectorAll('.close-video-modal').forEach(btn => {
      btn.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });

    // Закрытие по Escape
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  /**
   * Показать лоадер
   */
  showLoader(message = 'Генерируем видео...') {
    const loader = document.getElementById('glx');
    if (loader) {
      loader.classList.remove('hidden');
      const title = document.getElementById('glxTitle');
      const phase = document.getElementById('glxPhase');
      if (title) title.textContent = message;
      if (phase) phase.textContent = 'Обработка';
      this.updateLoaderProgress(0);
    }
  }

  /**
   * Обновить лоадер
   */
  updateLoader(message, percent) {
    const title = document.getElementById('glxTitle');
    if (title) title.textContent = message;
    this.updateLoaderProgress(percent);
  }

  /**
   * Скрыть лоадер
   */
  hideLoader() {
    const loader = document.getElementById('glx');
    if (loader) {
      loader.classList.add('hidden');
    }
  }

  /**
   * Обновить прогресс лоадера
   */
  updateLoaderProgress(percent) {
    const bar = document.getElementById('glxBar');
    const pct = document.getElementById('glxPct');

    if (bar) bar.style.width = `${percent}%`;
    if (pct) pct.textContent = `${Math.round(percent)}%`;
  }

  /**
   * Показать инструкции по проверке на Runware
   */
  showRunwareInstructions(runwareUrl, jobId) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4';
    modal.innerHTML = `
      <div class="bg-[var(--bg-card)] rounded-2xl max-w-2xl w-full p-6 border border-[var(--bord)] shadow-2xl">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-xl font-bold">🎬 Видео отправлено на генерацию!</h3>
          <button class="close-modal w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--bord)] transition-colors">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="space-y-4 mb-6">
          <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
            <p class="text-sm">
              <strong>Видео генерируется на серверах Runware.</strong><br>
              Процесс занимает <strong>30-60 секунд</strong>.
            </p>
          </div>

          <div class="space-y-2">
            <p class="font-medium">📋 Как проверить результат:</p>
            <ol class="list-decimal list-inside space-y-2 text-sm text-[var(--muted)]">
              <li>Откройте ссылку ниже в новой вкладке</li>
              <li>Подождите 30-60 секунд пока видео готовится</li>
              <li>Скачайте готовое видео с Runware</li>
              <li>Или вставьте ссылку на видео в поле ниже</li>
            </ol>
          </div>

          <a href="${runwareUrl}" target="_blank" class="block p-4 bg-[var(--bord)] hover:bg-[var(--bord)]/70 rounded-lg transition-colors">
            <div class="flex items-center justify-between">
              <span class="text-sm font-mono text-blue-400">${runwareUrl}</span>
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
            </div>
          </a>

          <div class="pt-4">
            <label class="block text-sm font-medium mb-2">Или вставьте ссылку на готовое видео:</label>
            <div class="flex gap-2">
              <input type="text" id="manual-video-url" placeholder="https://..."
                     class="field flex-1 text-sm font-mono">
              <button class="btn-video-submit px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors">
                Сохранить
              </button>
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <a href="${runwareUrl}" target="_blank" class="btn primary flex-1">
            Открыть Runware
          </a>
          <button class="btn secondary flex-1 close-modal">
            Закрыть
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Закрытие
    const closeModal = () => {
      modal.remove();
    };

    modal.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', closeModal);
    });

    // Ручной ввод URL
    const submitBtn = modal.querySelector('.btn-video-submit');
    submitBtn?.addEventListener('click', async () => {
      const urlInput = modal.querySelector('#manual-video-url');
      const videoUrl = urlInput?.value.trim();

      if (!videoUrl) {
        alert('Введите ссылку на видео');
        return;
      }

      if (!videoUrl.startsWith('http')) {
        alert('Ссылка должна начинаться с http:// или https://');
        return;
      }

      closeModal();
      this.showVideoResult(videoUrl, jobId, null);
    });
  }

  /**
   * Показать ошибку
   */
  showError(message) {
    // Используем простой alert, можно заменить на красивое модальное окно
    alert(message);
  }

  /**
   * Получить CSRF токен
   */
  getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  // Проверяем, что мы на странице генерации
  if (document.getElementById('video-generation-form')) {
    window.videoGeneration = new VideoGeneration();
    console.log('Модуль генерации видео инициализирован');
  }
});
