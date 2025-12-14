/**
 * Модуль генерации видео
 * Управляет формой генерации видео, отправкой запросов и отображением результатов
 */

class VideoGeneration {
  constructor() {
    const root = document.getElementById('gen-root') || document.body;
    this.userKey = (root && root.dataset && root.dataset.userKey) ? root.dataset.userKey : 'anon';

    // Clean up old localStorage keys without user isolation
    this.cleanupOldKeys();

    this.currentMode = 't2v'; // i2v или t2v (по умолчанию t2v — текст→видео, чтобы не требовать фото)
    this.selectedModel = null;
    this.models = [];
    this.fieldManager = null; // Field visibility manager
    this.sourceImage = null;
    this.sourcePreviewUrl = null; // DataURL превью для I2V плитки
    this.providerFields = {}; // Хранилище значений специфичных полей
    this.queue = this.loadQueue ? this.loadQueue() : []; // Персистентная очередь (pending/done)
    this.clearedJobs = (this.loadClearedJobs ? this.loadClearedJobs() : new Set()); // Очищенные из UI pending-задачи
    this.clearedTiles = new WeakSet(); // Ссылки на скрытые плитки без job_id
    this.clearedAt = (this.loadClearedAt ? this.loadClearedAt() : 0); // Persisted across reloads to suppress old results
    // Auto-translate toggle (persisted)
    this.autoTranslate = this.getSavedAutoTranslate ? this.getSavedAutoTranslate() : true;
    // Persisted jobs (button clicked) per user/session
    this.persistedJobs = this.loadPersistedJobs ? this.loadPersistedJobs() : new Set();
    this.isGenerating = false;

    this.init();
  }

  async init() {
    // Bind UI listeners as early as possible so buttons work even before models load
    this.setupEventListeners();
    // Init auto-translate toggle UI
    this.initAutoTranslateToggle && this.initAutoTranslateToggle();
    this.loadModels().then(() => { try { this.updateModelSelect(); } catch (_) { } });
    // Ensure proper initial visibility for mode-specific sections (incl. I2V compact upload)
    this.switchMode(this.currentMode);
    // Pre-render queue UI for instant display
    this.ensureQueueUI();
    // TTL purge at startup and then hourly to auto-clean queue after 24h
    this.purgeExpiredQueue?.();
    if (!this._ttlTimer) {
      this._ttlTimer = setInterval(() => { try { this.purgeExpiredQueue(); } catch (_) { } }, 60 * 60 * 1000);
    }
    // Restore queue with completed jobs only
    this.restoreQueue?.();
    // Load completed jobs from server (only finished results), scheduled after first paint
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => { try { this.bootstrapCompletedJobs?.(); } catch (_) { } });
    } else {
      setTimeout(() => { try { this.bootstrapCompletedJobs?.(); } catch (_) { } }, 0);
    }
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
        // Ошибка на уровне ответа — снимаем inflight
        try { localStorage.removeItem('gen.video.inflight'); } catch (_) { }
        console.error('Ошибка загрузки моделей:', data.error);
        this.showError('Не удалось загрузить модели видео');
      }
    } catch (error) {
      console.error('Ошибка при загрузке моделей:', error);
      this.showError('Ошибка подключения к серверу');
    }
  }

  /**
   * Обновление списка моделей: карточки с Tailwind вместо select
   */
  updateModelSelect() {
    const cardsContainer = document.getElementById('model-cards');
    const hiddenInput = document.getElementById('video-model'); // скрытое поле
    if (!cardsContainer || !hiddenInput) return;

    // Ensure compact horizontal scroller with 3-in-row cards + arrow controls
    try {
      // one-time CSS
      if (!document.getElementById('video-models-horizontal-style')) {
        const st = document.createElement('style');
        st.id = 'video-models-horizontal-style';
        st.textContent = `
#model-cards{display:flex!important;flex-wrap:nowrap!important;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px;-ms-overflow-style:none;scrollbar-width:none}
#model-cards::-webkit-scrollbar{display:none}
#model-cards .model-card-wrap{flex:0 0 calc(33.333% - 8px);scroll-snap-align:start}
/* compact hero height */
#model-cards .vm-hero{min-height:150px!important}
/* arrow buttons */
.vmodel-nav-btn{position:absolute;top:50%;transform:translateY(-50%);z-index:10;width:34px;height:34px;border-radius:9999px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.55);color:#fff;border:1px solid rgba(255,255,255,.25);box-shadow:0 2px 8px rgba(0,0,0,.25)}
.vmodel-nav-btn.disabled{opacity:.4;pointer-events:none;filter:grayscale(.4)}
html[data-theme="light"] .vmodel-nav-btn{background:rgba(0,0,0,.5);border-color:rgba(0,0,0,.15)}
.vmodel-nav-btn:hover{background:rgba(0,0,0,.75)}
.vmodel-nav-btn.left{left:4px}
.vmodel-nav-btn.right{right:4px}
        `;
        document.head.appendChild(st);
      }
      // arrows (once per container parent)
      // Force inline styles to ensure flex scroller overrides any grid CSS
      try {
        cardsContainer.style.display = 'flex';
        cardsContainer.style.flexWrap = 'nowrap';
        cardsContainer.style.overflowX = 'auto';
      } catch (_) { }

      const parent = cardsContainer.parentElement || cardsContainer;
      if (parent) {
        if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';
        if (!parent.querySelector('.vmodel-nav-btn.left')) {
          const mk = (dir) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'vmodel-nav-btn ' + (dir < 0 ? 'left' : 'right');
            b.setAttribute('aria-label', dir < 0 ? 'Назад' : 'Вперёд');
            b.innerHTML = dir < 0
              ? '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>'
              : '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>';
            b.addEventListener('click', () => {
              try {
                const gap = 12;
                const cardWidth = Math.round((cardsContainer.clientWidth - gap * 2) / 3);
                const delta = Math.max(160, cardWidth + gap);
                cardsContainer.scrollBy({ left: dir * delta, behavior: 'smooth' });
              } catch (_) { }
            });
            parent.appendChild(b);
          };
          mk(-1); mk(1);
          // Update arrows disabled state (start/end)
          const updateArrows = () => {
            const leftB = parent.querySelector('.vmodel-nav-btn.left');
            const rightB = parent.querySelector('.vmodel-nav-btn.right');
            const atStart = (cardsContainer.scrollLeft || 0) <= 1;
            const atEnd = (cardsContainer.scrollLeft + cardsContainer.clientWidth) >= (cardsContainer.scrollWidth - 1);
            if (leftB) leftB.classList.toggle('disabled', atStart);
            if (rightB) rightB.classList.toggle('disabled', atEnd);
          };
          // Enforce exactly 3 cards visible in viewport by fixing item width
          const GAP = 12;
          let __rzTimer = 0;
          const enforceThreeInView = () => {
            try {
              const viewport = cardsContainer.clientWidth || 900;
              // min card width safety to avoid too small tiles on narrow screens
              const cw = Math.max(220, Math.floor((viewport - GAP * 2) / 3));
              cardsContainer.querySelectorAll('.model-card-wrap').forEach(wrap => {
                wrap.style.flex = `0 0 ${cw}px`;
                wrap.style.maxWidth = `${cw}px`;
              });
              updateArrows();
            } catch (_) { }
          };
          enforceThreeInView();
          cardsContainer.addEventListener('scroll', updateArrows, { passive: true });
          window.addEventListener('resize', () => {
            clearTimeout(__rzTimer);
            __rzTimer = setTimeout(enforceThreeInView, 100);
          }, { passive: true });
        }
      }
    } catch (_) { }

    // Фильтруем модели по текущему режиму
    let filteredModels;
    if (this.currentMode === 'i2v') {
      // I2V: показываем все модели с category === 'i2v'
      filteredModels = this.models.filter(m => m.category === 'i2v');
    } else {
      // T2V: показываем все модели с category === 't2v'
      filteredModels = this.models.filter(m => m.category === 't2v');
    }

    // Рекомендуемая модель по режиму (для автовыбора/сортировки)
    const recommendedModelId = (this.currentMode === 'i2v') ? 'runware:201@1' : 'vidu:1@5';

    // Ставим рекомендуемую модель первой в списке, если она присутствует
    filteredModels.sort((a, b) => {
      const ida = (a.model_id || '').toLowerCase();
      const idb = (b.model_id || '').toLowerCase();
      if (ida === recommendedModelId) return -1;
      if (idb === recommendedModelId) return 1;
      return 0;
    });

    if (filteredModels.length === 0) {
      cardsContainer.innerHTML = '<div class="text-xs sm:text-sm text-[var(--muted)]">Нет доступных моделей</div>';
      this.selectedModel = null;
      hiddenInput.value = '';
      return;
    }

    const currentSelectedId = this.selectedModel ? this.selectedModel.id : null;
    const recommended = filteredModels.find(m => (m.model_id || '').toLowerCase() === recommendedModelId);
    const recommendedId = recommended ? recommended.id : null;

    const cardHtml = (model, isActive) => {
      const idLower = (model.model_id || '').toLowerCase();
      let name = model.name || 'Без названия';
      const cost = model.token_cost || 20;
      const duration = model.max_duration || 8;
      const provider = this.getProvider(model.model_id) || '';
      const category = (model.category || '').toUpperCase();
      const desc = this.escapeHtml(model.description || '');
      const vis = this.getModelVisuals(model);
      // Используем загруженное изображение модели если есть, иначе fallback
      const modelImageUrl = model.image_url || vis.bg;
      // Бейдж над карточкой в зависимости от режима/модели
      const badgeHtml = (() => {
        const green = (txt) => `
          <svg class="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <span class="text-[11px] sm:text-xs font-medium text-emerald-600 dark:text-emerald-400">${txt}</span>
        `;
        const red = (txt) => `
          <svg class="w-3.5 h-3.5 text-rose-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <span class="text-[11px] sm:text-xs font-medium text-rose-600 dark:text-rose-400">${txt}</span>
        `;
        const yellow = (txt) => `
          <svg class="w-3.5 h-3.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <span class="text-[11px] sm:text-xs font-medium text-amber-600 dark:text-amber-400">${txt}</span>
        `;
        const id = idLower;
        if (this.currentMode === 'i2v') {
          // Оживить фото:
          // - Wan2.5‑Preview: зелёная звёздочка «рекомендуем»
          if (id === 'runware:201@1') return green('рекомендуем');
          return '';
        } else {
          // Создать видео:
          // - Vidu 1.5: зелёная звёздочка «рекомендуем»
          // - Остальные: жёлтая звёздочка «премиум качество, звук»
          if (id === 'vidu:1@5') return green('рекомендуем');
          return yellow('премиум качество, звук');
        }
      })();

      return `
        <div class="model-card-wrap" data-id="${model.id}">

          <div class="h-5 sm:h-6 mb-1 flex items-center gap-1">
            ${badgeHtml}
          </div>

          <div class="model-card relative rounded-xl border-2 border-[var(--bord)]
                      bg-[var(--card)] cursor-pointer overflow-hidden
                      transition-all duration-300 hover:shadow-lg"
               data-id="${model.id}"
               data-selected="${isActive ? '1' : '0'}"
               role="button"
               tabindex="0"
               aria-label="Выбрать модель ${name}"
               aria-selected="${isActive ? 'true' : 'false'}">

            <!-- Image with Name & Description INSIDE -->
            <div class="vm-hero relative aspect-[16/9] overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900">
              <img src="/static/img/small-bg.png"
                   data-src="${modelImageUrl}"
                   alt="${name}"
                   class="lazy-img absolute inset-0 w-full h-full object-contain will-change-transform"
                   loading="lazy"
                   decoding="async"
                   fetchpriority="low"
                   width="1200" height="675"
                   style="filter:blur(4px);transform:scale(1.01)"
                   onerror="this.dataset.src='/static/img/small-bg.png'">

              <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20"></div>

              <div class="absolute top-2 left-2 w-2 h-2 rounded-full bg-primary animate-pulse ${isActive ? '' : 'hidden'}" data-role="selected-dot"></div>

              <!-- Top badge -->
              <div class="absolute top-2 right-2 px-2 py-1 rounded-md bg-black/60 backdrop-blur-sm text-white text-[10px] sm:text-xs font-semibold uppercase">
                ${category || provider}
              </div>

              <!-- Name & Description CENTERED -->
              <div class="absolute inset-0 flex flex-col items-center justify-center px-4 text-center">
                <h3 class="js-model-name text-white font-bold text-base sm:text-lg mb-2 drop-shadow-lg whitespace-normal break-words">
                  ${name}
                </h3>
                <p class="text-white/90 text-xs sm:text-sm leading-snug drop-shadow-md line-clamp-2">
                  ${desc}
                </p>
                <p class="text-white/75 text-[10px] sm:text-xs mt-2 leading-tight">
                  <span class="font-medium">Лучше для:</span> ${this.escapeHtml(vis.best)}
                </p>
              </div>
            </div>

            <!-- Compact info row under image: small, neat chips with equal heights and theme-aware colors -->
            <div class="p-2.5 sm:p-3">
              <div class="grid grid-cols-3 gap-1.5">
                <!-- Cost -->
                <div class="flex items-center justify-center gap-2 h-9 rounded-lg bg-[var(--bord)]/50">
                  <span class="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center">
                    <span class="w-2 h-2 rounded-full bg-primary"></span>
                  </span>
                  <div class="flex items-baseline gap-1">
                    <span class="text-xs sm:text-sm font-bold tabular-nums text-[var(--text)]">${cost}</span>
                    <span class="text-[10px] text-[var(--muted)] uppercase">TOK</span>
                  </div>
                </div>

                <!-- Duration -->
                <div class="flex items-center justify-center gap-2 h-9 rounded-lg bg-[var(--bord)]/50">
                  <span class="w-4 h-4 rounded-full bg-[var(--fg)]/10 flex items-center justify-center">
                    <svg class="w-2.5 h-2.5 text-[var(--fg)]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                  </span>
                  <div class="flex items-baseline gap-1">
                    <span class="text-xs sm:text-sm font-bold tabular-nums text-[var(--text)]">${duration}</span>
                    <span class="text-[10px] text-[var(--muted)]">с</span>
                  </div>
                </div>

                <!-- Provider -->
                <div class="flex items-center justify-center gap-2 h-9 rounded-lg bg-[var(--bord)]/50">
                  <span class="w-4 h-4 rounded-full bg-[var(--fg)]/10 flex items-center justify-center">
                    <svg class="w-2.5 h-2.5 text-[var(--fg)]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                      <path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path>
                    </svg>
                  </span>
                  <span class="text-[10px] sm:text-xs font-semibold uppercase tracking-wide text-[var(--text)]">${provider}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    };

    // Рендер карточек
    cardsContainer.innerHTML = filteredModels.map((m, idx) => {
      const isActive = currentSelectedId
        ? (m.id === currentSelectedId)
        : (recommendedId ? (m.id === recommendedId) : (idx === 0));
      return cardHtml(m, isActive);
    }).join('');

    // Инициализация ленивой подгрузки картинок карточек (плейсхолдер -> реальный src при появлении)
    this.setupLazyImages(cardsContainer);

    // Убираем грид‑классы шаблона и жёстко фиксируем поведение «1 строка, горизонтальная лента»
    try {
      cardsContainer.classList.remove('grid', 'grid-cols-1', 'xs:grid-cols-2', 'lg:grid-cols-3', 'gap-2', 'sm:gap-3');
      cardsContainer.style.display = 'flex';
      cardsContainer.style.flexWrap = 'nowrap';
      cardsContainer.style.overflowX = 'auto';
      cardsContainer.style.overflowY = 'hidden';
    } catch (_) { }

    // После рендера карточек — принудительно пересчитать ширину итемов под «ровно 3 в кадре»
    try { if (typeof enforceThreeInView === 'function') enforceThreeInView(); } catch (_) { }

    // Обновить состояние стрелок после первичного рендера
    try { cardsContainer.dispatchEvent(new Event('scroll')); } catch (_) { }

    // Установить выбранную модель
    let selected = null;
    if (currentSelectedId) {
      selected = filteredModels.find(m => m.id === currentSelectedId) || filteredModels[0];
    } else {
      selected = (recommendedId ? filteredModels.find(m => m.id === recommendedId) : null) || filteredModels[0];
    }
    this.selectedModel = selected;

    // Синхронизируем скрытое поле и вызываем обработчики
    hiddenInput.value = String(selected.id);
    hiddenInput.dispatchEvent(new Event('change'));

    // Индикация выбранной карточки (показываем точку). Рамку задаёт CSS по data-selected
    cardsContainer.querySelectorAll('.model-card').forEach(card => {
      const isSel = card.dataset.selected === '1';
      const dot = card.querySelector('[data-role="selected-dot"]');
      if (dot) dot.classList.toggle('hidden', !isSel);
      card.setAttribute('aria-selected', isSel ? 'true' : 'false');
    });

    // Листенеры выбора карточек (по клику на карточку, мета или обёртку)
    cardsContainer.querySelectorAll('.model-card, .model-card-meta, .model-card-wrap').forEach(el => {
      el.addEventListener('click', (ev) => {
        // Ignore clicks directly on the model name label (non-clickable text)
        if (ev && ev.target && ev.target.closest && ev.target.closest('.js-model-name')) return;
        const wrap = el.closest('.model-card-wrap') || el;
        const id = parseInt((wrap && wrap.dataset.id) || el.dataset.id);
        const model = filteredModels.find(m => m.id === id);
        if (!model) return;

        // Сбрасываем выделение со всех карточек (только data-selected, рамку рисует CSS)
        cardsContainer.querySelectorAll('.model-card').forEach(c => {
          c.dataset.selected = '0';
          c.setAttribute('aria-selected', 'false');
          c.querySelector('[data-role="selected-dot"]')?.classList.add('hidden');
        });

        // Выделяем выбранную
        const activeCard = wrap.querySelector('.model-card');
        if (activeCard) {
          activeCard.dataset.selected = '1';
          activeCard.setAttribute('aria-selected', 'true');
          activeCard.querySelector('[data-role="selected-dot"]')?.classList.remove('hidden');
        }

        // Обновляем состояние
        this.selectedModel = model;
        hiddenInput.value = String(model.id);
        hiddenInput.dispatchEvent(new Event('change'));

        // Обновляем зависящие элементы
        this.updateCost();
        this.updateDurationLimit();
        this.updateResolutionOptions();
        this.updateCameraOptions();
        this.updateProviderFields();
        this.updateModelDescription();
        this.updateModelInfo();
        // Обновляем видимость полей на основе конфигурации модели
        if (window.VideoFieldManager) {
          if (!this.fieldManager) {
            this.fieldManager = new window.VideoFieldManager();
          }
          this.fieldManager.updateFieldsForModel(model);
        }
        // updateFPSOptions вызывается ПОСЛЕ VideoFieldManager чтобы корректно скрыть секцию если только 1 значение FPS
        this.updateFPSOptions();
      });
    });

    // Обновляем связанные блоки при первичном рендере
    this.updateCost();
    this.updateDurationLimit();
    this.updateResolutionOptions();
    this.updateCameraOptions();
    this.updateProviderFields();
    this.updateModelDescription();
    this.updateModelInfo();
    // Обновляем видимость полей на основе конфигурации модели при первичном рендере
    if (window.VideoFieldManager && this.selectedModel) {
      if (!this.fieldManager) {
        this.fieldManager = new window.VideoFieldManager();
      }
      this.fieldManager.updateFieldsForModel(this.selectedModel);
    }
    // updateFPSOptions вызывается ПОСЛЕ VideoFieldManager чтобы корректно скрыть секцию если только 1 значение FPS
    this.updateFPSOptions();
  }

  /**
   * Обновление описания модели
   */
  updateModelDescription() {
    const contentEl = document.getElementById('model-description-content');
    if (!contentEl || !this.selectedModel) return;

    const description = this.selectedModel.description;
    if (description && description.trim()) {
      contentEl.innerHTML = this.escapeHtml(description);
    } else {
      contentEl.innerHTML = '<em>Описание недоступно</em>';
    }
  }

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

    // Обновляем видимость секции референсов
    this.updateReferenceSection();
  }

  /**
   * Экранирование HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Compute pretty aspect text like 21:9, 16:9, 9:16, 4:3, 3:2, 1:1 based on width/height
   * Keeps the frame unchanged; this is purely informational.
   */
  computeAspectText(w, h) {
    if (!w || !h) return '';
    const ratio = w / h;
    // Known common aspects
    const known = [
      { txt: '21:9', val: 21 / 9 },
      { txt: '16:9', val: 16 / 9 },
      { txt: '9:16', val: 9 / 16 },
      { txt: '4:3', val: 4 / 3 },
      { txt: '3:2', val: 3 / 2 },
      { txt: '1:1', val: 1 }
    ];
    // Find closest known within tolerance
    let best = { txt: '', diff: Number.POSITIVE_INFINITY };
    known.forEach(k => {
      const d = Math.abs(ratio - k.val);
      if (d < best.diff) best = { txt: k.txt, diff: d };
    });
    // Accept if close enough; else reduce fraction
    if (best.diff <= 0.03) return best.txt;

    // Generic reduction
    const gcd = (a, b) => b ? gcd(b, a % b) : a;
    const g = gcd(Math.round(w), Math.round(h)) || 1;
    const rw = Math.round(w / g);
    const rh = Math.round(h / g);
    return `${rw}:${rh}`;
  }

  /**
   * Update I2V aspect UI chip next to preview (show/hide)
   */
  setI2VAspectInfo(text) {
    const wrap = document.getElementById('i2v-aspect-info');
    const label = document.getElementById('i2v-aspect-text');
    if (!wrap || !label) return;
    if (text && String(text).trim() !== '') {
      label.textContent = text;
      wrap.classList.remove('hidden');
    } else {
      label.textContent = '—';
      wrap.classList.add('hidden');
    }
  }

  // Clean up old localStorage keys without user isolation
  cleanupOldKeys() {
    try {
      const oldKeys = ['gen.video.queue', 'gen.video.clearedJobs', 'gen.video.pendingJob', 'gen.video.inflight', 'gen.video.autoTranslate'];
      oldKeys.forEach(key => {
        if (localStorage.getItem(key)) {
          localStorage.removeItem(key);
        }
      });

      // Also clean up keys from other users
      const allKeys = Object.keys(localStorage);
      allKeys.forEach(key => {
        if (key.startsWith('gen.video.queue::') && !key.endsWith(`::${this.userKey}`)) {
          localStorage.removeItem(key);
        }
        if (key.startsWith('gen.video.clearedJobs::') && !key.endsWith(`::${this.userKey}`)) {
          localStorage.removeItem(key);
        }
        if (key.startsWith('gen.video.pendingJob::') && !key.endsWith(`::${this.userKey}`)) {
          localStorage.removeItem(key);
        }
      });
    } catch (_) { }
  }

  // ===== Персистентная очередь генераций =====
  loadQueue() {
    try {
      const raw = localStorage.getItem(`gen.video.queue::${this.userKey}`);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (_) { return []; }
  }

  saveQueue() {
    try {
      localStorage.setItem(`gen.video.queue::${this.userKey}`, JSON.stringify(this.queue.slice(-24)));
    } catch (_) { }
  }

  loadClearedJobs() {
    try {
      const raw = localStorage.getItem(`gen.video.clearedJobs::${this.userKey}`);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr.map(String) : []);
    } catch (_) { return new Set(); }
  }

  saveClearedJobs() {
    try {
      localStorage.setItem(`gen.video.clearedJobs::${this.userKey}`, JSON.stringify(Array.from(this.clearedJobs)));
    } catch (_) { }
  }

  // Persist/restore global clear timestamp to avoid resurrecting old results after reload
  loadClearedAt() {
    try {
      const v = localStorage.getItem(`gen.video.clearedAt::${this.userKey}`);
      return parseInt(v || '0', 10) || 0;
    } catch (_) {
      return 0;
    }
  }

  saveClearedAt(ts) {
    try { localStorage.setItem(`gen.video.clearedAt::${this.userKey}`, String(ts || 0)); } catch (_) { }
  }

  // ===== Persisted jobs (user pressed "Добавить в мои генерации") =====
  loadPersistedJobs() {
    try {
      const raw = localStorage.getItem(`gen.video.persisted::${this.userKey}`);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr.map(String) : []);
    } catch (_) { return new Set(); }
  }

  savePersistedJobs() {
    try {
      localStorage.setItem(`gen.video.persisted::${this.userKey}`, JSON.stringify(Array.from(this.persistedJobs)));
    } catch (_) { }
  }

  // Cache result assets in Cache Storage (fallback to IndexedDB if absent)
  cacheAsset(url) {
    try {
      if (url && 'caches' in window) {
        caches.open('gen-assets-v1').then(c => c.add(url)).catch(() => { });
      }
    } catch (_) { }
  }

  // Eager load: instant video attach with connection hints and autoplay (muted)
  lazyLoadVideo(videoEl, url) {
    try {
      if (!videoEl || !url) return;

      // Preconnect / DNS Prefetch / Preload hints for the video origin
      try {
        const u = new URL(url, location.href);
        const origin = u.origin;

        if (!document.querySelector(`link[rel="preconnect"][href="${origin}"]`)) {
          const l1 = document.createElement('link');
          l1.rel = 'preconnect';
          l1.href = origin;
          l1.crossOrigin = 'anonymous';
          document.head.appendChild(l1);
        }
        if (!document.querySelector(`link[rel="dns-prefetch"][href="${origin}"]`)) {
          const l2 = document.createElement('link');
          l2.rel = 'dns-prefetch';
          l2.href = origin;
          document.head.appendChild(l2);
        }
        if (!document.querySelector(`link[rel="preload"][as="video"][href="${url}"]`)) {
          const l3 = document.createElement('link');
          l3.rel = 'preload';
          l3.as = 'video';
          l3.href = url;
          document.head.appendChild(l3);
        }
      } catch (_) { }

      // Eager load and attempt autoplay for instant visual feedback
      try { videoEl.preload = 'auto'; } catch (_) { }
      try { videoEl.src = url; } catch (_) { }
      if (typeof videoEl.load === 'function') {
        try { videoEl.load(); } catch (_) { }
      }
      if (typeof videoEl.play === 'function') {
        const p = videoEl.play();
        if (p && typeof p.catch === 'function') {
          p.catch(() => { /* ignore autoplay policy rejections */ });
        }
      }
    } catch (_) { }
  }

  // Lightweight lazy image loader for model cards: заменяем placeholder src на data-src по IntersectionObserver
  ensureImageLazyObserver() {
    try {
      if (this._imgIO) return;
      this._imgIO = new IntersectionObserver((entries) => {
        entries.forEach((ent) => {
          if (!ent.isIntersecting) return;
          const img = ent.target;
          const real = (img.dataset && img.dataset.src) ? img.dataset.src : '';
          if (real) {
            try { img.src = real; } catch (_) { }
          }
          // убрать блюр/скейл после загрузки реального изображения
          try {
            img.addEventListener('load', () => {
              try { img.style.filter = ''; img.style.transform = ''; } catch (_) { }
            }, { once: true });
          } catch (_) { }
          // атрибуты низкой стоимости декодирования
          try {
            img.loading = 'lazy';
            img.decoding = 'async';
            img.setAttribute('fetchpriority', 'low');
          } catch (_) { }
          try { this._imgIO.unobserve(img); } catch (_) { }
        });
      }, { rootMargin: '150px 0px' });
    } catch (_) { }
  }

  setupLazyImages(rootEl) {
    try {
      if (!rootEl) return;
      this.ensureImageLazyObserver();
      const list = rootEl.querySelectorAll('img.lazy-img');
      list.forEach((img) => {
        try {
          if (this._imgIO) this._imgIO.observe(img);
          img.loading = 'lazy';
          img.decoding = 'async';
          img.setAttribute('fetchpriority', 'low');
        } catch (_) { }
      });
    } catch (_) { }
  }

  // Create queue UI lazily only when first generation starts or when restoring pending items
  ensureQueueUI() {
    const wrap = document.getElementById('video-form-container');
    if (!wrap) return;

    // If grid already exists (создан ранее), обновим его классы сетки под новую компоновку и выйдем
    const existingGrid = document.getElementById('video-results-grid');
    if (existingGrid) {
      // Убираем inline стили чтобы CSS из video-queue-compact-style применился
      try {
        existingGrid.style.gridTemplateColumns = '';
        existingGrid.style.gap = '';
      } catch (_) { }
      return;
    }

    // Card container
    const card = document.createElement('div');
    card.id = 'video-queue-card';
    card.className = 'card p-6 mt-6';

    card.innerHTML = `
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <h3 class="text-lg sm:text-xl font-bold">Очередь генерации</h3>
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-xs bg-primary/15 text-primary border border-primary/30"
                title="Результаты видео и эскизы хранятся локально 24 часа, затем удаляются автоматически">
            24&nbsp;ч
          </span>
        </div>
        <button type="button" id="clear-video-queue-btn" class="px-3 py-1.5 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] text-xs sm:text-sm">
          Очистить очередь
        </button>
      </div>
      <div class="mt-2 rounded-xl border border-[var(--bord)] bg-[var(--bg-card)] p-3 text-xs text-[var(--muted)]">
        Результаты (видео) хранятся локально 24 часа. По истечении срока очередь очищается автоматически. Данные не покидают ваш браузер.
      </div>
      <div id="video-results-grid" class="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3"></div>
    `;

    // Insert after prompts/showcase blocks within video form container
    wrap.appendChild(card);
    // Lightweight performance styles for offscreen results
    if (!document.getElementById('video-queue-perf-style')) {
      const st = document.createElement('style');
      st.id = 'video-queue-perf-style';
      st.textContent = `
        #video-results-grid{content-visibility:auto;contain-intrinsic-size:800px}
      `;
      try { document.head.appendChild(st); } catch (_) { }
    }
    // Принудительно задаём компактную сетку через ID-селектор (обходит отсутствие новых классов в Tailwind)
    // Увеличенные карточки на 25%: minmax(300px, 1fr) для более крупного отображения видео
    if (!document.getElementById('video-queue-compact-style')) {
      const st2 = document.createElement('style');
      st2.id = 'video-queue-compact-style';
      st2.textContent = `
        #video-results-grid {
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem;
        }
        /* Responsive: на средних экранах */
        @media (max-width: 768px) {
          #video-results-grid {
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 0.75rem;
          }
        }
        /* Responsive: на маленьких экранах */
        @media (max-width: 640px) {
          #video-results-grid {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 0.5rem;
          }
        }
        /* Responsive: на очень маленьких экранах */
        @media (max-width: 480px) {
          #video-results-grid {
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 0.5rem;
          }
        }
        @media (max-width: 380px) {
          #video-results-grid {
            grid-template-columns: 1fr;
            gap: 0.5rem;
          }
        }
      `;
      try { document.head.appendChild(st2); } catch (_) { }
    }

    // Bind clear button to clear queue and remove UI immediately
    const clearBtn = card.querySelector('#clear-video-queue-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        try { this.clearQueue(); } catch (_) { }
        try { if (card && card.isConnected) card.remove(); } catch (_) { }
      });
    }
  }

  // "Show more" button for deferred appending of extra video results
  insertShowMoreButton(grid) {
    try {
      if (!grid || grid._hasShowMore) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = grid.id + '-show-more';
      btn.className = 'mt-4 w-full px-3 py-2 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] text-sm hover:border-primary/60 hover:text-primary transition';
      btn.textContent = 'Показать ещё';
      const parent = grid.parentElement || grid;
      parent.appendChild(btn);
      grid._hasShowMore = true;

      btn.addEventListener('click', () => {
        try {
          const list = grid._moreJobs || [];
          const frag = document.createDocumentFragment();
          const batch = list.splice(0, 12);
          batch.forEach(job => {
            const tile = this.createPendingTile();
            if (job && job.video_url) {
              this.renderTileResult(tile, job.video_url, job.job_id, job.gallery_id);
              frag.appendChild(tile);
            }
          });
          grid.appendChild(frag);
          if (!list.length) { btn.remove(); grid._hasShowMore = false; }
        } catch (_) { }
      });
    } catch (_) { }
  }

  // Пометить конкретную плитку как очищенную пользователем, не влияя на генерацию/галерею
  markTileCleared(tile) {
    try {
      if (!tile) return;
      tile.dataset.cleared = '1';
      this.clearedTiles?.add(tile);
      const jid = tile.dataset.jobId;
      if (jid) {
        this.clearedJobs.add(String(jid));
        this.saveClearedJobs?.();
        // Фикс: глобально помечаем момент очистки и убираем возможные «залипшие» pending-флаги
        this.clearedAt = Date.now();
        this.saveClearedJobs();
        try {
          localStorage.removeItem('gen.video.pendingJob');
          localStorage.removeItem('gen.video.inflight');
        } catch (_) { }
      }
      if (tile && tile.isConnected) tile.remove();
    } catch (_) { }
  }

  addOrUpdateQueueEntry(jobId, patch) {
    if (!jobId) return;
    const id = String(jobId);

    // НЕ добавляем задачи, которые пользователь явно удалил
    if (this.clearedJobs && this.clearedJobs.has(id)) {
      console.log('[addOrUpdateQueueEntry] BLOCKED - job is in clearedJobs:', id);
      return;
    }

    const idx = this.queue.findIndex(e => String(e.job_id) === id);
    if (idx >= 0) {
      this.queue[idx] = { ...this.queue[idx], ...patch, job_id: id };
    } else {
      this.queue.push({ job_id: id, createdAt: Date.now(), ...patch });
    }
    this.saveQueue();
  }

  // Purge items older than 24h from UI queue and DOM (strict)
  // Any items without createdAt are treated as expired and are marked as cleared forever.
  purgeExpiredQueue() {
    try {
      const TTL_MS = 24 * 60 * 60 * 1000;
      const now = Date.now();
      const removed = new Set();
      const next = (this.queue || []).filter(e => {
        const ok = e && e.createdAt && (now - e.createdAt) < TTL_MS;
        if (!ok && e && e.job_id) removed.add(String(e.job_id));
        return ok;
      });
      if (next.length !== (this.queue || []).length) {
        this.queue = next;
        this.saveQueue();

        // Mark expired jobs as cleared so they never re-appear from bootstrapCompletedJobs
        if (removed.size && this.clearedJobs) {
          try {
            removed.forEach(id => this.clearedJobs.add(String(id)));
            this.saveClearedJobs && this.saveClearedJobs();
          } catch (_) { }
        }

        // Remove tiles for purged jobs
        const grid = document.getElementById('video-results-grid');
        if (grid && removed.size) {
          grid.querySelectorAll('.video-result-tile').forEach(tile => {
            const jid = tile && tile.dataset ? tile.dataset.jobId : null;
            if (jid && removed.has(String(jid))) {
              try { tile.remove(); } catch (_) { }
            }
          });
          // If grid is empty, hide the card until next generation
          if (!grid.querySelector('.video-result-tile')) {
            const card = document.getElementById('video-queue-card');
            if (card) { try { card.remove(); } catch (_) { } }
          }
        }
      }
    } catch (_) { }
  }

  // Persist job in "Мои генерации"
  async persistJob(jobId, btn) {
    if (!jobId) return;
    try {
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Добавляем…';
      }
      const r = await fetch(`/generate/api/job/${jobId}/persist`, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.getCSRFToken(), 'X-Requested-With': 'fetch' },
        credentials: 'same-origin'
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || j.ok === false) throw new Error(j.error || ('HTTP ' + r.status));
      // mark persisted in local storage
      try {
        if (!this.persistedJobs) this.persistedJobs = new Set();
        this.persistedJobs.add(String(jobId));
        this.savePersistedJobs && this.savePersistedJobs();
      } catch (_) { }

      // No auto-download here — по требованию: добавляем в «Мои генерации» без скачивания

      if (btn) {
        btn.textContent = 'Добавлено';
        btn.disabled = true;
        btn.classList.add('opacity-70', 'pointer-events-none', 'animate-pulse');
        // brief success pulse anim
        try { setTimeout(() => btn.classList.remove('animate-pulse'), 600); } catch (_) { }
      }
    } catch (e) {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Добавить в мои генерации';
      }
      try { console.warn('Persist failed', e); } catch (_) { }
    }
  }

  restoreQueue() {
    try {
      const now = Date.now();
      const TTL_24H = 24 * 60 * 60 * 1000; // 24 часа

      const items = [...this.queue].sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
      if (!items.length) return;

      this.ensureQueueUI();
      const grid = document.getElementById('video-results-grid');
      if (!grid) return;

      const frag = document.createDocumentFragment();
      const toRemove = [];

      items.forEach(item => {
        // 1. Проверяем что задача не удалена пользователем
        if (this.clearedJobs && this.clearedJobs.has(String(item.job_id))) {
          return;
        }

        // 2. Автоудаление задач старше 24 часов
        const completedAt = item.completedAt || item.createdAt || 0;
        if (completedAt && (now - completedAt > TTL_24H)) {
          toRemove.push(item.job_id);
          if (item.job_id) {
            this.clearedJobs.add(String(item.job_id));
          }
          return;
        }

        // 3. Skip legacy mixed-in IMAGE entries (no video_url but has image_url)
        if (item && !item.video_url && item.image_url) {
          try { this.clearedJobs.add(String(item.job_id)); this.saveClearedJobs(); } catch (_) { }
          return;
        }
        let tile = this.createPendingTile(item.preview || null);
        if (item.status === 'done' && item.video_url) {
          this.renderTileResult(tile, item.video_url, item.job_id, item.gallery_id);
        } else if (item.status === 'failed') {
          this.renderTileError(tile, item.error || 'Ошибка при генерации видео');
        } else {
          this.setTileProgress(tile, 10, 'Возобновляем…');
          this.pollVideoStatusInline(item.job_id, tile);
        }
        frag.appendChild(tile);
      });

      // Удаляем устаревшие задачи из очереди
      if (toRemove.length > 0) {
        this.queue = this.queue.filter(item => !toRemove.includes(item.job_id));
        this.saveQueue();
        this.saveClearedJobs();
      }

      grid.appendChild(frag);
      if (grid._moreJobs && grid._moreJobs.length && typeof this.insertShowMoreButton === 'function') {
        this.insertShowMoreButton(grid);
      }
    } catch (_) { }
  }

  async clearQueue() {
    try {
      const grid = document.getElementById('video-results-grid');

      // backend: permanently clear server-side queue for this owner
      try {
        await fetch('/generate/api/queue/clear', { method: 'POST', headers: { 'X-CSRFToken': this.getCSRFToken() }, credentials: 'same-origin' });
      } catch (_) { }

      // 1) Помечаем ВСЕ задачи (и pending, и done) как очищенные, чтобы их результаты не вернулись в грид
      this.queue.forEach(e => {
        if (e.job_id) this.clearedJobs.add(String(e.job_id));
      });
      this.saveClearedJobs();
      console.log('[clearQueue] Saved clearedJobs:', Array.from(this.clearedJobs));

      // 2) Глобально запоминаем момент очистки и сбрасываем возможные «залипшие» pending-флаги
      this.clearedAt = Date.now();
      this.saveClearedAt(this.clearedAt);
      console.log('[clearQueue] Saved clearedAt:', this.clearedAt);
      try {
        localStorage.removeItem('gen.video.pendingJob');
        localStorage.removeItem('gen.video.inflight');
      } catch (_) { }

      // 3) Удаляем из DOM все плитки (и pending, и done)
      if (grid) {
        grid.querySelectorAll('.video-result-tile').forEach(el => {
          try { if (el.isConnected) el.remove(); } catch (_) { }
        });
      }

      // 4) Полностью очищаем локальную очередь (UI-очередь)
      this.queue = [];
      this.saveQueue();

      // 5) Скрыть UI очереди до следующего запуска генерации
      try {
        const card = document.getElementById('video-queue-card');
        if (card && card.isConnected) card.remove();
      } catch (_) { }
    } catch (_) { }
  }

  /**
   * Получить провайдера из model_id
   */
  getProvider(modelId) {
    if (!modelId || typeof modelId !== 'string') return '';
    return modelId.split(':')[0].toLowerCase();
  }

  /**
   * Подбор фона и "лучше для" по model_id/provider/category
   * Возвращает { bg, best }
   */
  getModelVisuals(model) {
    const id = (model?.model_id || '').toLowerCase();
    const provider = this.getProvider(id);
    const cat = (model?.category || '').toLowerCase();

    // Runway Gen-4 Turbo visuals (T2V)
    if (id === 'runway:1@1') {
      return {
        bg: '/static/img/category/Портрет.jpg',
        best: 'быстрая генерация видео, кинематографичное качество, плавные движения'
      };
    }

    // Runway Gen-4 Turbo I2V visuals
    if (id === 'runway:1@1-i2v') {
      return {
        bg: '/static/img/category/Портрет.jpg',
        best: 'оживление фото, естественные движения, сохранение деталей'
      };
    }

    // Wan2.5-Preview visuals
    if (id === 'runware:201@1') {
      return { bg: '/static/img/category/Портрет.jpg', best: 'оживление фото, естественная мимика и свет' };
    }

    // Точные соответствия популярных моделей
    const map = {
      'google:3@0': { bg: '/static/img/category/города.jpg', best: 'премиум-реализм, сцены с людьми и продуктами, реклама' },
      'google:2@0': { bg: '/static/img/category/Пейзаж.jpg', best: 'реалистичные текстуры, интерьер/экстерьер, предметка' },
      'vidu:1@5': { bg: '/static/img/category/технологии.jpg', best: 'динамичные T2V ролики 4–8 сек, движущиеся сцены' },
      'vidu:1@1': { bg: '/static/img/category/Портрет.jpg', best: 'оживление фото (I2V): портреты и предметные съёмки' },
      'pixverse:1@0': { bg: '/static/img/category/Искусство.jpg', best: 'стилизация, трендовые эффекты и художественные ролики' },
      'openai:3@2': { bg: '/static/img/category/будущее.jpg', best: 'Sora 2 Pro: кинематографичный реализм, 4/8/12 сек, 30 FPS' }
    };
    if (map[id]) return map[id];

    // Фолбэки по провайдеру/категории
    if (provider === 'google') return { bg: '/static/img/category/города.jpg', best: 'реализм, кинематографическая картинка' };
    if (provider === 'vidu') return { bg: '/static/img/category/Пейзаж.jpg', best: 'кинематографичные сцены и движения камеры' };
    if (provider === 'pixverse') return { bg: '/static/img/category/Искусство.jpg', best: 'стилизация и фирменные эффекты' };
    if (cat === 'anime') return { bg: '/static/img/category/мода.jpg', best: 'аниме/иллюстративный стиль' };
    if (cat === 'i2v') return { bg: '/static/img/category/Портрет.jpg', best: 'оживление фотографий' };
    return { bg: '/static/img/small-bg.png', best: 'универсальные сцены' };
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
          type: 'select',
          id: 'bytedance-fps',
          name: 'fps',
          label: 'Частота кадров (FPS)',
          description: 'ByteDance поддерживает только 24 FPS',
          options: [
            { value: '24', label: '24 FPS' }
          ],
          default: '24'
        },
        {
          type: 'select',
          id: 'bytedance-format',
          name: 'outputFormat',
          label: 'Формат вывода',
          options: [
            { value: 'mp4', label: 'MP4' }
          ],
          default: 'mp4'
        },
        {
          type: 'select',
          id: 'bytedance-height',
          name: 'height',
          label: 'Высота (px)',
          options: [
            { value: '480', label: '480' }
          ],
          default: '480'
        },
        {
          type: 'select',
          id: 'bytedance-width',
          name: 'width',
          label: 'Ширина (px)',
          options: [
            { value: '864', label: '864' }
          ],
          default: '864'
        },
        {
          type: 'select',
          id: 'bytedance-results',
          name: 'numberResults',
          label: 'Количество результатов',
          description: 'Больше результатов = выше стоимость',
          options: [
            { value: '1', label: '1' },
            { value: '2', label: '2' },
            { value: '3', label: '3' },
            { value: '4', label: '4' }
          ],
          default: '2'
        },
        {
          type: 'number',
          id: 'bytedance-seed',
          name: 'seed',
          label: 'Seed',
          description: '-1 для случайного значения',
          placeholder: '-1',
          default: '-1'
        },
        {
          type: 'range',
          id: 'bytedance-quality',
          name: 'outputQuality',
          label: 'Качество вывода (%)',
          description: 'Выше качество = больший размер файла',
          min: 20,
          max: 99,
          step: 1,
          default: 95
        },
        {
          type: 'checkbox',
          id: 'bytedance-include-cost',
          name: 'includeCost',
          label: 'Включить стоимость в ответ',
          description: 'Показывать информацию о затратах токенов',
          default: true
        },
        {
          type: 'checkbox',
          id: 'bytedance-camera-fixed',
          name: 'camera_fixed',
          label: 'Фиксированная камера',
          description: 'Камера остается неподвижной на протяжении всего видео',
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
      'openai': [
        {
          type: 'select',
          id: 'openai-fps',
          name: 'fps',
          label: 'Частота кадров (FPS)',
          options: [{ value: '30', label: '30 FPS' }],
          default: '30'
        },
        {
          type: 'select',
          id: 'openai-format',
          name: 'outputFormat',
          label: 'Формат вывода',
          options: [{ value: 'mp4', label: 'MP4' }],
          default: 'mp4'
        },
        {
          type: 'select',
          id: 'openai-results',
          name: 'numberResults',
          label: 'Количество результатов',
          options: [
            { value: '1', label: '1' },
            { value: '2', label: '2' },
            { value: '3', label: '3' },
            { value: '4', label: '4' }
          ],
          default: '2'
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
    } else if (field.type === 'number') {
      const placeholder = field.placeholder || '';
      const defaultVal = field.default || '';
      return `
        <div>
          <label class="block text-sm font-medium mb-2" for="${field.id}">
            ${field.label}
          </label>
          ${field.description ? `
            <p class="text-xs text-[var(--muted)] mb-2">${field.description}</p>
          ` : ''}
          <input type="number" id="${field.id}" name="${field.name}"
                 value="${defaultVal}" placeholder="${placeholder}"
                 class="field w-full">
        </div>
      `;
    } else if (field.type === 'range') {
      const min = field.min || 0;
      const max = field.max || 100;
      const step = field.step || 1;
      const defaultVal = field.default || min;
      return `
        <div>
          <label class="block text-sm font-medium mb-2" for="${field.id}">
            ${field.label}
          </label>
          ${field.description ? `
            <p class="text-xs text-[var(--muted)] mb-2">${field.description}</p>
          ` : ''}
          <div class="relative">
            <input type="range" id="${field.id}" name="${field.name}"
                   min="${min}" max="${max}" step="${step}" value="${defaultVal}"
                   class="w-full h-2 bg-[var(--bord)] rounded-lg appearance-none cursor-pointer slider-thumb">
            <div class="flex justify-between text-xs text-[var(--muted)] mt-1">
              <span>${min}%</span>
              <span id="${field.id}-value" class="font-medium text-primary">${defaultVal}%</span>
              <span>${max}%</span>
            </div>
          </div>
        </div>
      `;
    } else if (field.type === 'textarea') {
      const rows = field.rows || 2;
      const placeholder = field.placeholder ? `placeholder="${field.placeholder}"` : '';
      return `
        <div>
          <label class="block text-sm font-medium mb-2" for="${field.id}">
            ${field.label}
          </label>
          ${field.description ? `
            <p class="text-xs text-[var(--muted)] mb-2">${field.description}</p>
          ` : ''}
          <textarea id="${field.id}" name="${field.name}" rows="${rows}" ${placeholder}
                    class="field w-full resize-y min-h-[72px]"></textarea>
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

    // Для ByteDance: обработчик слайдера качества
    if (provider === 'bytedance') {
      const qualitySlider = document.getElementById('bytedance-quality');
      const qualityValue = document.getElementById('bytedance-quality-value');

      if (qualitySlider && qualityValue) {
        qualitySlider.addEventListener('input', function () {
          qualityValue.textContent = this.value + '%';

          // Обновляем градиент слайдера
          const min = parseInt(this.min);
          const max = parseInt(this.max);
          const percent = ((this.value - min) / (max - min)) * 100;
          this.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percent}%, var(--bord) ${percent}%, var(--bord) 100%)`;
        });

        // Инициализируем градиент
        const min = parseInt(qualitySlider.min);
        const max = parseInt(qualitySlider.max);
        const percent = ((qualitySlider.value - min) / (max - min)) * 100;
        qualitySlider.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percent}%, var(--bord) ${percent}%, var(--bord) 100%)`;
      }
    }

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
   * Обновление UI длительности по модели:
   * - Использует available_durations из API
   * - Если доступна только одна длительность — скрываем секцию
   * - Иначе рисуем набор «пилюль» из доступных значений
   */
  updateDurationLimit() {
    if (!this.selectedModel) return;

    const section = document.getElementById('duration-section');
    const options = document.getElementById('duration-options');
    const hidden = document.getElementById('video-duration');
    if (!section || !options || !hidden) return;

    // Получаем доступные длительности из модели (API возвращает массив)
    let availableDurations = this.selectedModel.available_durations || [];

    // Если нет доступных длительностей, используем max_duration
    if (availableDurations.length === 0) {
      const maxDuration = this.selectedModel.max_duration || 10;
      availableDurations = [maxDuration];
    }

    // Если доступна только одна длительность — ВСЕГДА скрываем выбор
    // Это имеет приоритет над optional_fields.duration
    if (availableDurations.length <= 1) {
      section.style.display = 'none';
      hidden.value = availableDurations[0] || 5;
      console.log('[VideoGeneration] Duration section hidden - only one duration available:', availableDurations[0]);
      return;
    }

    // Показываем выбор длительности (только если больше одной опции)
    section.style.display = '';

    // Сортируем длительности по возрастанию
    const durations = [...availableDurations].sort((a, b) => a - b);

    // Текущее значение или первое доступное
    const current = parseInt(hidden.value, 10) || durations[0];

    // Рендерим пилюли
    options.innerHTML = durations.map(d => `
      <button type="button"
              class="duration-pill px-3 py-1.5 rounded-xl border border-[var(--bord)] bg-[var(--bg-card)] text-xs sm:text-sm hover:border-primary/60 hover:text-primary ${d === current ? 'border-primary/60 text-primary bg-primary/10' : ''}"
              data-value="${d}">
        ${d} сек
      </button>
    `).join('');

    // Навесить обработчики на пилюли
    options.querySelectorAll('.duration-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        options.querySelectorAll('.duration-pill').forEach(b => {
          b.classList.remove('border-primary/60', 'text-primary', 'bg-primary/10');
        });
        btn.classList.add('border-primary/60', 'text-primary', 'bg-primary/10');
        hidden.value = btn.dataset.value;
      });
    });
  }

  /**
   * Обновление опций разрешения на основе доступных разрешений модели
   */
  updateResolutionOptions() {
    if (!this.selectedModel) return;

    const select = document.getElementById('video-resolution');
    if (!select) return;

    const availableResolutions = this.selectedModel.available_resolutions || [];

    if (availableResolutions.length === 0) {
      // Fallback к стандартным разрешениям
      availableResolutions.push('1920x1080', '1280x720', '1080x1920');
    }

    // Группируем по соотношению сторон
    const landscape = [];
    const portrait = [];
    const square = [];

    availableResolutions.forEach(res => {
      const [w, h] = res.split('x').map(Number);
      if (w === h) {
        square.push(res);
      } else if (w > h) {
        landscape.push(res);
      } else {
        portrait.push(res);
      }
    });

    // Строим optgroups
    let html = '';

    if (landscape.length > 0) {
      html += '<optgroup label="📺 Ландшафт">';
      landscape.forEach(res => {
        html += `<option value="${res}">${res}</option>`;
      });
      html += '</optgroup>';
    }

    if (portrait.length > 0) {
      html += '<optgroup label="📱 Портрет">';
      portrait.forEach(res => {
        html += `<option value="${res}">${res}</option>`;
      });
      html += '</optgroup>';
    }

    if (square.length > 0) {
      html += '<optgroup label="⬜ Квадрат">';
      square.forEach(res => {
        html += `<option value="${res}">${res}</option>`;
      });
      html += '</optgroup>';
    }

    select.innerHTML = html;
  }

  /**
   * Обновление опций движения камеры на основе доступных движений модели
   */
  updateCameraOptions() {
    if (!this.selectedModel) return;

    const select = document.getElementById('video-camera');
    if (!select) return;

    const availableMovements = this.selectedModel.available_camera_movements || [];

    // Всегда добавляем опцию "Авто"
    let html = '<option value="">Авто</option>';

    if (availableMovements.length > 0) {
      availableMovements.forEach(movement => {
        html += `<option value="${movement.value}">${movement.label}</option>`;
      });
    } else {
      // Fallback к стандартным движениям
      html += '<option value="static">Static (статичная)</option>';
      html += '<option value="slow pan">Slow Pan (панорама)</option>';
      html += '<option value="orbit">Orbit (орбита)</option>';
      html += '<option value="dolly">Dolly (наезд/отъезд)</option>';
    }

    select.innerHTML = html;
  }

  /**
   * Обновление опций FPS на основе доступных значений модели
   * Допустимые значения: 15, 24, 30, 60, 90, 120
   * Если доступно только одно значение - скрываем выбор или делаем его неактивным
   */
  updateFPSOptions() {
    if (!this.selectedModel) return;

    const fpsParam = document.getElementById('fps-param');
    const fpsSelect = document.getElementById('video-fps');
    const fpsHint = document.getElementById('fps-hint');

    if (!fpsSelect) return;

    // Получаем доступные FPS из модели (API возвращает массив)
    const availableFPS = this.selectedModel.available_fps || [];
    const fpsRange = this.selectedModel.fps_range || {};
    const defaultFPS = fpsRange.default || 30;

    // Если модель не поддерживает FPS или нет доступных значений - скрываем секцию
    if (!this.selectedModel.supports_fps || availableFPS.length === 0) {
      if (fpsParam) fpsParam.style.display = 'none';
      return;
    }

    // Показываем секцию FPS (даже если только 1 значение - пользователь должен видеть настройку)
    if (fpsParam) fpsParam.style.display = '';

    // Сортируем FPS по возрастанию
    const sortedFPS = [...availableFPS].sort((a, b) => a - b);

    // Строим опции select
    let html = '';
    sortedFPS.forEach(fps => {
      const isSelected = fps === defaultFPS ? 'selected' : '';
      html += `<option value="${fps}" ${isSelected}>${fps} FPS</option>`;
    });

    fpsSelect.innerHTML = html;

    // Показываем подсказку если доступно несколько значений
    if (fpsHint) {
      fpsHint.style.display = sortedFPS.length > 1 ? '' : 'none';
    }

    // Устанавливаем значение по умолчанию если текущее не в списке
    const currentValue = parseInt(fpsSelect.value, 10);
    if (!sortedFPS.includes(currentValue)) {
      fpsSelect.value = defaultFPS || sortedFPS[0];
    }
  }

  /**
   * Настройка обработчиков событий
   */
  setupEventListeners() {
    // Переключатель T2V / I2V
    document.querySelectorAll('.video-source-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const source = e.currentTarget.dataset.source;
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
          this.updateModelDescription();
          this.updateModelInfo();
        }
      });
    }

    // Пилюли силы движения (для I2V)
    const motionContainer = document.getElementById('motion-options');
    const motionHidden = document.getElementById('video-motion-strength');
    if (motionContainer && motionHidden) {
      const setActive = (val) => {
        motionContainer.querySelectorAll('.motion-pill').forEach(b => {
          const active = String(b.dataset.value) === String(val);
          b.classList.toggle('border-primary/60', active);
          b.classList.toggle('text-primary', active);
          b.classList.toggle('bg-primary/10', active);
        });
        motionHidden.value = val;
      };
      motionContainer.querySelectorAll('.motion-pill').forEach(btn => {
        btn.addEventListener('click', () => setActive(btn.dataset.value));
      });
      // Инициализация по умолчанию
      setActive(motionHidden.value || '60');
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

    // Загрузка референсных изображений и аудио
    this.setupReferenceUploads();

    // Кнопка генерации
    const generateBtn = document.getElementById('generate-video-btn');
    if (generateBtn) {
      generateBtn.addEventListener('click', () => this.generateVideoMulti());
    }

    // Кнопка очистки очереди (только ожидания, готовые видео не трогаем)
    const clearBtn = document.getElementById('clear-video-queue-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearQueue());
    }

    // Перехват кликов по кнопке удаления конкретной плитки (делегирование)
    const resultsGrid = document.getElementById('video-results-grid');
    if (resultsGrid) {
      resultsGrid.addEventListener('click', (e) => {
        // Persist to "Мои генерации"
        const pbtn = e.target.closest('.persist-btn');
        if (pbtn) {
          const tile = pbtn.closest('.video-result-tile');
          const jid = tile && tile.dataset ? tile.dataset.jobId : null;
          if (jid) { this.persistJob(String(jid), pbtn); }
          return;
        }

        // Remove tile from queue UI
        const btn = e.target.closest('.tile-remove-btn');
        if (!btn) return;
        const tile = btn.closest('.video-result-tile');
        if (!tile) return;
        const jid = tile.dataset.jobId;
        if (jid) {
          // backend: permanently remove this job
          try {
            fetch('/generate/api/queue/remove', {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': this.getCSRFToken() },
              credentials: 'same-origin',
              body: 'job_id=' + encodeURIComponent(String(jid))
            });
          } catch (_) { }
          this.clearedJobs.add(String(jid));
          this.saveClearedJobs();
        } else {
          this.clearedTiles?.add(tile);
        }
        try { if (tile.isConnected) tile.remove(); } catch (_) { }
      });
    }

    // Popover для описания модели (будет пропущен, если кнопка/popover не присутствуют в DOM)
    this.setupModelPopover();
  }

  /**
   * Автоперевод промпта — инициализация и UI
   */
  initAutoTranslateToggle() {
    try {
      const btn = document.getElementById('auto-translate-toggle');
      if (!btn) return;
      // Initial UI from persisted state
      btn.setAttribute('aria-pressed', this.autoTranslate ? 'true' : 'false');
      this.applyAutoTranslateUI(btn, this.autoTranslate);

      btn.addEventListener('click', () => {
        const on = btn.getAttribute('aria-pressed') !== 'true';
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        this.autoTranslate = !!on;
        this.saveAutoTranslate?.(this.autoTranslate);
        this.applyAutoTranslateUI(btn, this.autoTranslate);
      });
    } catch (_) { }
  }

  applyAutoTranslateUI(btn, on) {
    try {
      // Button background states
      btn.classList.toggle('bg-[var(--bord)]', !on);
      btn.classList.toggle('bg-primary/90', on);
      btn.classList.toggle('ring-primary/40', on);
      // Dot position (fallback to inline transform to avoid purge issues)
      const dot = btn.querySelector('.dot');
      if (dot) {
        dot.style.transform = on ? 'translateX(20px)' : 'translateX(0px)';
        dot.classList.add('bg-white');
      }
    } catch (_) { }
  }

  getSavedAutoTranslate() {
    try {
      const v = localStorage.getItem('gen.video.autoTranslate');
      if (v === null || v === undefined) return true; // default ON
      return v === '1' || v === 'true';
    } catch (_) { return true; }
  }

  saveAutoTranslate(on) {
    try { localStorage.setItem('gen.video.autoTranslate', on ? '1' : '0'); } catch (_) { }
  }

  /**
   * Настройка popover для описания модели
   */
  setupModelPopover() {
    const infoBtn = document.getElementById('model-info-btn');
    const popover = document.getElementById('model-description-popover');
    const content = document.getElementById('model-description-content');
    const closeBtn = document.getElementById('close-model-popover');

    if (!infoBtn || !popover || !content || !closeBtn) return;

    const showPopover = () => {
      if (this.selectedModel && this.selectedModel.description) {
        this.updateModelDescription();
        popover.classList.remove('hidden');
        // Позиционирование относительно кнопки
        const buttonRect = infoBtn.getBoundingClientRect();
        popover.style.position = 'fixed';
        popover.style.top = `${buttonRect.bottom + window.scrollY + 8}px`;
        popover.style.left = `${buttonRect.left + window.scrollX}px`;
        popover.style.width = '280px';
        console.log('Popover positioned at:', popover.style.top, popover.style.left);
      }
    };

    const hidePopover = () => {
      popover.classList.add('hidden');
    };

    // Показать на hover и click
    infoBtn.addEventListener('mouseenter', showPopover);
    infoBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (popover.classList.contains('hidden')) {
        showPopover();
      } else {
        hidePopover();
      }
    });

    // Скрыть на клик вне popover
    document.addEventListener('click', (e) => {
      if (!popover.contains(e.target) && !infoBtn.contains(e.target)) {
        hidePopover();
      }
    });

    // Закрыть кнопку
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      hidePopover();
    });

    // Скрыть при скролле
    window.addEventListener('scroll', hidePopover, { passive: true });
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
    // Показ/скрытие компактной загрузки фото под промптом
    const i2vCompact = document.getElementById('i2v-upload-compact');
    if (i2vCompact) {
      i2vCompact.style.display = mode === 'i2v' ? 'block' : 'none';
    }

    // Обновляем список моделей
    this.updateModelSelect();

    // Обновляем информацию о референсах в зависимости от режима
    this.updateReferenceSection();
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
        this.sourcePreviewUrl = null;
        this.sourceAspectText = '';
        fileInput.value = '';
        if (preview) preview.classList.add('hidden');
        uploadArea.style.display = 'block';
        // Hide aspect chip
        this.setI2VAspectInfo('');
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
      // Сохраняем превью для плитки ожидания (I2V)
      this.sourcePreviewUrl = e.target.result;

      // Compute and show detected aspect ratio for the source image (display only)
      try {
        const probe = new Image();
        probe.onload = () => {
          const arText = this.computeAspectText(probe.naturalWidth || probe.width, probe.naturalHeight || probe.height);
          this.sourceAspectText = arText;
          this.setI2VAspectInfo(arText);
        };
        probe.src = e.target.result;
      } catch (_) { /* no-op */ }
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
      } else if (field.type === 'number') {
        const value = element.value;
        if (value && value !== '-1') {
          values[field.name] = parseInt(value);
        }
      } else if (field.type === 'range') {
        const value = element.value;
        if (value) {
          values[field.name] = parseInt(value);
        }
      } else if (field.type === 'textarea') {
        const value = (element.value || '').trim();
        if (value) {
          values[field.name] = value;
        }
      }
    });

    // Для ByteDance: обработка camera_fixed в providerSettings
    if (provider === 'bytedance') {
      const cameraFixed = document.getElementById('bytedance-camera-fixed')?.checked;
      if (cameraFixed) {
        values.providerSettings = {
          bytedance: {
            cameraFixed: true
          }
        };
      }
    }

    // I2V audio input (URL/UUID/DataURI)
    try {
      const audioUrlEl = document.getElementById('i2v-audio-url');
      const audioUrl = audioUrlEl && audioUrlEl.value ? audioUrlEl.value.trim() : '';
      if (audioUrl) {
        values.audioInputs = [audioUrl];
      }
    } catch (_) { }
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
    formData.append('auto_translate', (this.autoTranslate ? '1' : '0'));
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

    // Number of videos to generate
    const numberVideos = document.getElementById('video-quantity')?.value || '1';
    formData.append('number_videos', numberVideos);

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

    // Сворачиваем блок режима и создаем плитку ожидания в результатах
    const modeBlock = document.getElementById('video-mode-block');
    if (modeBlock) modeBlock.style.display = 'none';

    this.ensureQueueUI();
    const resultsGrid = document.getElementById('video-results-grid');
    let tile = null;
    if (resultsGrid) {
      tile = this.createPendingTile();
      // Новый запрос — выше остальных
      resultsGrid.prepend(tile);
    }

    try {
      const response = await fetch('/generate/api/video/submit', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'X-Requested-With': 'fetch'
        }
      });

      const data = await response.json();

      if (data.success) {
        // Проверяем мгновенный результат
        if (data.status === 'done' && data.video_url) {
          try { this.cacheAsset(data.video_url); } catch (_) { }
          try { localStorage.removeItem(`gen.video.pendingJob::${this.userKey}`); } catch (_) { }
          if (tile) {
            this.renderTileResult(tile, data.video_url, data.job_id, data.gallery_id);
          } else {
            // fallback
            this.showVideoResult(data.video_url, data.job_id, data.gallery_id);
          }
        } else {
          // Начинаем inline-polling
          if (data.job_id) { try { localStorage.setItem(`gen.video.pendingJob::${this.userKey}`, String(data.job_id)); } catch (_) { } }
          if (tile) this.setTileProgress(tile, 5, 'Генерация видео…');
          this.pollVideoStatusInline(data.job_id, tile);
        }
      } else {
        // Ошибка ответа — снимаем inflight
        try { localStorage.removeItem('gen.video.inflight'); } catch (_) { }
        if (tile) {
          this.renderTileError(tile, data.error || 'Ошибка при генерации видео');
        } else {
          this.showError(data.error || 'Ошибка при генерации видео');
        }
      }
    } catch (error) {
      console.error('Ошибка при отправке запроса:', error);
      try { localStorage.removeItem('gen.video.inflight'); } catch (_) { }
      if (tile) {
        this.renderTileError(tile, 'Ошибка при отправке запроса. Попробуйте позже.');
      } else {
        this.showError('Ошибка при отправке запроса. Попробуйте позже.');
      }
    }
  }

  /**
   * Генерация видео с поддержкой множественных результатов (fan-out)
   * Если пользователь выбрал numberResults > 1, отправляем N независимых задач,
   * создаём N плиток и ведём отдельный polling для каждой.
   */
  async generateVideoMulti() {
    const prompt = document.getElementById('video-prompt')?.value.trim();
    if (!prompt) { this.showError('Пожалуйста, введите описание сцены'); return; }
    if (!this.selectedModel) { this.showError('Пожалуйста, выберите модель'); return; }

    // Для I2V проверяем наличие изображения
    if (this.currentMode === 'i2v' && !this.sourceImage) {
      this.showError('Пожалуйста, загрузите исходное изображение');
      return;
    }

    // Prevent double-start on rapid clicks
    if (this.isGenerating) return;
    this.isGenerating = true;

    // Базовые параметры из формы (значения одинаковы для всех fan-out задач)
    const duration = document.getElementById('video-duration')?.value || 5;
    const activeRatioBtn = document.querySelector('.aspect-ratio-btn.active');
    const aspectRatio = activeRatioBtn?.dataset.ratio || '16:9';
    const resolution = document.getElementById('video-resolution')?.value || '1920x1080';
    const camera = document.getElementById('video-camera')?.value || '';
    const seedInput = (document.getElementById('video-seed')?.value || '').trim();

    // Поля провайдера
    const providerFields = this.collectProviderFields();
    const numResults = parseInt(
      (providerFields.numberResults ?? providerFields.number_results ?? 1), 10
    ) || 1;

    // Прячем блок с настройками и готовим контейнер для результатов
    const modeBlock = document.getElementById('video-mode-block');
    if (modeBlock) modeBlock.style.display = 'none';
    this.ensureQueueUI();
    const resultsGrid = document.getElementById('video-results-grid');

    // Отправляем N независимых задач (каждая с numberResults=1)
    for (let i = 0; i < numResults; i++) {
      // Создаём плитку для каждой задачи
      let tile = null;
      if (resultsGrid) {
        tile = this.createPendingTile();
        resultsGrid.prepend(tile);
      }

      // Готовим FormData для одной задачи
      const fd = new FormData();
      fd.append('prompt', prompt);
      fd.append('auto_translate', this.autoTranslate ? '1' : '0');
      fd.append('video_model_id', this.selectedModel.id);
      fd.append('generation_mode', this.currentMode);
      fd.append('duration', duration);
      fd.append('aspect_ratio', aspectRatio);
      fd.append('resolution', resolution);
      if (camera) fd.append('camera_movement', camera);

      // Пересчёт seed для уникальности результатов (если указан и не -1)
      if (seedInput && seedInput !== '-1') {
        const seedValue = String((parseInt(seedInput, 10) || 0) + i);
        fd.append('seed', seedValue);
      } else if (seedInput) {
        // '-1' или пустое не добавляем — сервер сгенерирует случайный
        fd.append('seed', seedInput);
      }

      // provider_fields: принудительно numberResults=1 для fan-out
      const perReqFields = { ...(providerFields || {}) };
      delete perReqFields.numberResults;
      delete perReqFields.number_results;
      perReqFields.numberResults = 1;
      if (Object.keys(perReqFields).length > 0) {
        fd.append('provider_fields', JSON.stringify(perReqFields));
      }

      // Для I2V добавляем изображение и силу движения
      if (this.currentMode === 'i2v') {
        fd.append('source_image', this.sourceImage);
        const motionStrength = document.getElementById('video-motion-strength')?.value || 45;
        fd.append('motion_strength', motionStrength);
      }

      // Для T2V добавляем референсное изображение (одно фото)
      if (this.currentMode === 't2v' && this.t2vReferenceFile) {
        fd.append('reference_images', this.t2vReferenceFile);
      }

      // Отправляем одну задачу последовательно, чтобы не блокировать SQLite
      await this.submitVideoRequest(fd, tile);
      // Небольшая пауза между запросами снижает риск "database is locked" на SQLite
      await this.sleep(120);
    }
    this.isGenerating = false;
  }

  /**
   * Отправка одной задачи генерации и обработка ответа
   */
  async submitVideoRequest(formData, tile) {
    try {
      const response = await fetch('/generate/api/video/submit', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'X-Requested-With': 'fetch'
        }
      });

      const data = await response.json();

      if (data.success) {
        if (data.status === 'done' && data.video_url) {
          try { localStorage.removeItem(`gen.video.pendingJob::${this.userKey}`); } catch (_) { }
          if (this.clearedJobs && this.clearedJobs.has(String(data.job_id))) {
            // Пользователь очистил очередь: не показываем плитку результата
            this.addOrUpdateQueueEntry(data.job_id, { status: 'done', video_url: data.video_url, gallery_id: data.gallery_id, completedAt: Date.now() });
            try { if (tile && tile.isConnected) tile.remove(); } catch (_) { }
            if (window.videoCache && data.cached_until) { try { await window.videoCache.store(data.job_id, data.video_url, data.cached_until); } catch (_) { } }
            return;
          }
          if (!tile || !tile.isConnected) {
            const grid = document.getElementById('video-results-grid');
            if (grid) {
              tile = this.createPendingTile();
              grid.prepend(tile);
            }
          }
          this.renderTileResult(tile, data.video_url, data.job_id, data.gallery_id);
        } else {
          if (data.job_id) {
            try { localStorage.setItem(`gen.video.pendingJob::${this.userKey}`, String(data.job_id)); } catch (_) { }
            try { this.addOrUpdateQueueEntry(data.job_id, { status: 'pending' }); } catch (_) { }
          }
          if (tile) this.setTileProgress(tile, 5, 'Генерация видео…');
          this.pollVideoStatusInline(data.job_id, tile);
        }
      } else {
        try { localStorage.removeItem('gen.video.inflight'); } catch (_) { }
        if (tile) {
          this.renderTileError(tile, data.error || 'Ошибка при генерации видео');
        } else {
          this.showError(data.error || 'Ошибка при генерации видео');
        }
      }
    } catch (error) {
      console.error('Ошибка при отправке запроса:', error);
      try { localStorage.removeItem('gen.video.inflight'); } catch (_) { }
      if (tile) {
        this.renderTileError(tile, 'Ошибка при отправке запроса. Попробуйте позже.');
      } else {
        this.showError('Ошибка при отправке запроса. Попробуйте позже.');
      }
    }
  }

  /**
   * Polling статуса генерации (inline в плитке)
   */
  async pollVideoStatusInline(jobId, tile, attempts = 0) {
    const maxAttempts = 360; // ~3 минуты при 500ms интервале
    // Быстрый polling: 500ms первые 60 попыток, затем 800ms
    const baseDelay = attempts < 60 ? 500 : 800;
    const delay = document.hidden ? baseDelay * 1.5 : baseDelay;
    // Персистим как pending
    if (jobId) { try { this.addOrUpdateQueueEntry(jobId, { status: 'pending' }); } catch (_) { } }

    if (attempts >= maxAttempts) {
      if (tile) this.setTileProgress(tile, 98, 'Почти готово…');
      setTimeout(() => this.pollVideoStatusInline(jobId, tile, attempts + 1), 10000);
      return;
    }

    try {
      const response = await fetch(`/generate/api/video/status/${jobId}`);
      if (response.status === 404 || response.status === 403) {
        try { this.clearedJobs.add(String(jobId)); this.saveClearedJobs(); } catch (_) { }
        try { if (tile && tile.isConnected) tile.remove(); } catch (_) { }
        return;
      }
      const data = await response.json();

      if (data.status === 'done' && data.video_url) {
        try { localStorage.removeItem(`gen.video.pendingJob::${this.userKey}`); } catch (_) { }

        // Фикс: если пользователь очистил очередь и задача была создана до этого момента — не показывать её результат
        try {
          const idx = this.queue.findIndex(e => String(e.job_id) === String(jobId));
          const createdAt = (idx >= 0 && this.queue[idx].createdAt) || 0;
          if (this.clearedAt && createdAt && createdAt <= this.clearedAt) {
            this.addOrUpdateQueueEntry(jobId, { status: 'done', video_url: data.video_url, gallery_id: data.gallery_id, completedAt: Date.now() });
            try { if (tile && tile.isConnected) tile.remove(); } catch (_) { }
            if (window.videoCache && data.cached_until) {
              try { await window.videoCache.store(jobId, data.video_url, data.cached_until); } catch (_) { }
            }
            return;
          }
        } catch (_) { }

        if (this.clearedJobs && this.clearedJobs.has(String(jobId))) {
          this.addOrUpdateQueueEntry(jobId, { status: 'done', video_url: data.video_url, gallery_id: data.gallery_id, completedAt: Date.now() });
          try { if (tile && tile.isConnected) tile.remove(); } catch (_) { }
          if (window.videoCache && data.cached_until) { try { await window.videoCache.store(jobId, data.video_url, data.cached_until); } catch (_) { } }
          return;
        }
        if (!tile || !tile.isConnected) {
          const grid = document.getElementById('video-results-grid');
          if (grid) {
            const newTile = this.createPendingTile();
            grid.prepend(newTile);
            tile = newTile;
          }
        }
        try { this.cacheAsset(data.video_url); } catch (_) { }
        this.renderTileResult(tile, data.video_url, jobId, data.gallery_id);
        if (window.videoCache && data.cached_until) {
          await window.videoCache.store(jobId, data.video_url, data.cached_until);
        }
      } else if (data.status === 'failed') {
        try { localStorage.removeItem(`gen.video.pendingJob::${this.userKey}`); } catch (_) { }
        if (tile) {
          this.renderTileError(tile, data.error || 'Ошибка при генерации видео');
        } else {
          this.showError(data.error || 'Ошибка при генерации видео');
        }
      } else {
        const p = (data && typeof data.progress === 'number')
          ? Math.min(98, data.progress)
          : Math.min(98, (attempts / maxAttempts) * 100);
        if (tile) this.setTileProgress(tile, p, 'Генерация видео…');
        setTimeout(() => this.pollVideoStatusInline(jobId, tile, attempts + 1), 10000);
      }
    } catch (error) {
      console.error('Ошибка при проверке статуса:', error);
      setTimeout(() => this.pollVideoStatusInline(jobId, tile, attempts + 1), 10000);
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
        try { localStorage.removeItem(`gen.video.pendingJob::${this.userKey}`); } catch (_) { }
        this.hideLoader();
        this.showVideoResult(data.video_url, jobId, data.gallery_id);

        // Сохраняем в IndexedDB кеш
        if (window.videoCache && data.cached_until) {
          await window.videoCache.store(jobId, data.video_url, data.cached_until);
        }
      } else if (data.status === 'failed') {
        try { localStorage.removeItem('gen.video.pendingJob'); } catch (_) { }
        this.hideLoader();
        this.showError(data.error || 'Ошибка при генерации видео');
      } else {
        // Обновляем прогресс (если сервер дал прогресс — используем его)
        const p = (data && typeof data.progress === 'number')
          ? Math.min(98, data.progress)
          : Math.min(98, (attempts / maxAttempts) * 100);
        this.updateLoader('Генерация видео...', p);

        // Продолжаем polling каждые 10 секунд
        setTimeout(() => this.pollVideoStatus(jobId, attempts + 1), 10000);
      }
    } catch (error) {
      console.error('Ошибка при проверке статуса:', error);
      // Продолжаем попытки при ошибке сети
      setTimeout(() => this.pollVideoStatus(jobId, attempts + 1), 10000);
    }
  }

  /**
   * Возобновить polling после перезагрузки страницы (UI-only)
   */
  resumePendingVideo() {
    try {
      const jobId = localStorage.getItem(`gen.video.pendingJob::${this.userKey}`);
      if (!jobId) return;
      this.ensureQueueUI();
      const grid = document.getElementById('video-results-grid');
      let tile = null;
      if (grid) {
        tile = this.createPendingTile();
        grid.prepend(tile);
        this.setTileProgress(tile, 10, 'Возобновляем…');
      }
      this.pollVideoStatusInline(jobId, tile);
    } catch (_) { }
  }

  /**
   * Restore completed jobs from server (only show finished results)
   */
  async bootstrapCompletedJobs() {
    try {
      const r = await fetch('/generate/api/completed-jobs?type=video', { headers: { 'X-Requested-With': 'fetch' } });
      let j = await r.json().catch(() => null);
      if (!j || !j.success || !j.jobs || !j.jobs.length) return;

      this.ensureQueueUI();
      const grid = document.getElementById('video-results-grid');
      if (!grid) return;
      const frag = document.createDocumentFragment();
      const LIMIT = 12;
      let shown = 0;
      grid._moreJobs = grid._moreJobs || [];

      // Show only completed VIDEO jobs for current user; ignore images and cleared-at or older
      j.jobs.forEach(job => {
        const jid = String(job.job_id);
        if (this.clearedJobs.has(jid)) {
          console.log('[bootstrapCompletedJobs] SKIP - in clearedJobs:', jid);
          return;
        }
        if (this.queue.some(e => String(e.job_id) === jid)) {
          console.log('[bootstrapCompletedJobs] SKIP - already in queue:', jid);
          return;
        }

        // respect last clear moment (skip items created before/at clear)
        const createdAtTs = job.created_at ? Date.parse(job.created_at) : 0;
        if (this.clearedAt && createdAtTs && createdAtTs <= this.clearedAt) {
          console.log('[bootstrapCompletedJobs] SKIP - older than clearedAt:', jid, createdAtTs, this.clearedAt);
          return;
        }

        // Only include videos in video queue
        if ((job.generation_type || 'image') !== 'video') return;
        if (!(job.status === 'done' && job.video_url)) return;

        if (shown < LIMIT) {
          const tile = this.createPendingTile();
          frag.appendChild(tile);
          this.renderTileResult(tile, job.video_url, jid, job.gallery_id);
          shown++;
        } else {
          grid._moreJobs.push({
            job_id: jid,
            video_url: job.video_url,
            gallery_id: job.gallery_id,
            status: 'done'
          });
        }

        this.addOrUpdateQueueEntry(jid, {
          status: 'done',
          video_url: job.video_url,
          gallery_id: job.gallery_id,
          completedAt: Date.now()
        });
      });
      grid.appendChild(frag);
    } catch (_) { }
  }

  /**
   * Создать плитку ожидания результата (inline)
   */
  createPendingTile(previewUrl = null) {
    const tile = document.createElement('div');
    // Добавляем анимацию появления
    tile.className = 'video-result-tile rounded-xl border border-[var(--bord)] bg-[var(--bg-card)] overflow-hidden shadow-sm animate-fade-in-scale';
    tile.setAttribute('data-status', 'pending');

    const hasPreview = !!(previewUrl || (this.currentMode === 'i2v' && this.sourcePreviewUrl));
    const pic = previewUrl || this.sourcePreviewUrl || null;

    // Aspect + TTL badges (display-only). Keep frame unchanged.
    const aspectText = (this.currentMode === 'i2v' && this.sourceAspectText) ? this.escapeHtml(this.sourceAspectText) : '';
    const badgesHtml = `
      </div>`;

    // Persist aspect on tile for later (result stage)
    if (aspectText) { try { tile.dataset.aspectText = aspectText; } catch (_) { } }

    tile.innerHTML = `
      <div class="relative aspect-video group ${hasPreview ? '' : 'bg-gradient-to-br from-[var(--bg-card)] to-[var(--bg-2)]'}">
        ${badgesHtml}
        ${hasPreview ? `<img src="${pic}" alt="Источник" class="absolute inset-0 w-full h-full object-cover">` : ''}

        <!-- Кнопка удаления СКРЫТА во время генерации -->

        <!-- Puzzle Loader (same as image loader), overlaid on top of preview if present -->
        <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4">
          <div class="puzzle-grid relative w-24 h-24 sm:w-28 sm:h-28">
            <div class="puzzle-piece puzzle-p1" style="--delay: 0s"></div>
            <div class="puzzle-piece puzzle-p2" style="--delay: 0.1s"></div>
            <div class="puzzle-piece puzzle-p3" style="--delay: 0.2s"></div>
            <div class="puzzle-piece puzzle-p4" style="--delay: 0.3s"></div>
            <div class="puzzle-piece puzzle-p5" style="--delay: 0.4s"></div>
            <div class="puzzle-piece puzzle-p6" style="--delay: 0.5s"></div>
            <div class="puzzle-piece puzzle-p7" style="--delay: 0.6s"></div>
            <div class="puzzle-piece puzzle-p8" style="--delay: 0.7s"></div>
            <div class="puzzle-piece puzzle-p9" style="--delay: 0.8s"></div>
          </div>

          <div class="text-center">
            <div class="text-sm sm:text-base font-semibold text-[var(--text)] mb-1" data-role="tile-phase">Создаём магию…</div>
            <div class="text-xs sm:text-sm text-[var(--muted)]" data-role="tile-status">Подготовка</div>
          </div>
        </div>

        <!-- Animated gradient overlay -->
        <div class="absolute inset-0 opacity-20 pointer-events-none">
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-primary/30 to-transparent animate-shimmer"></div>
        </div>
      </div>
    `;

    // Inject puzzle animation styles if not already present (parity with image loader)
    if (!document.getElementById('video-player-styles')) {
      const vstyle = document.createElement('style');
      vstyle.id = 'video-player-styles';
      vstyle.textContent = `
        /* Video player volume slider styles */
        .volume-slider {
          -webkit-appearance: none;
          appearance: none;
          background: rgba(255,255,255,0.3);
          border-radius: 9999px;
          height: 4px;
          cursor: pointer;
        }
        .volume-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          box-shadow: 0 1px 4px rgba(0,0,0,0.3);
          transition: transform 0.15s ease;
        }
        .volume-slider::-webkit-slider-thumb:hover {
          transform: scale(1.15);
        }
        .volume-slider::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          border: none;
          box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }
        .volume-slider::-moz-range-track {
          background: rgba(255,255,255,0.3);
          border-radius: 9999px;
          height: 4px;
        }
        /* Video tile aspect-video */
        .video-result-tile .aspect-video {
          aspect-ratio: 16/9;
        }
        /* Unified tile sizing for mobile */
        @media (max-width: 640px) {
          .video-result-tile, .image-result-tile {
            width: 100%;
          }
          .video-result-tile .aspect-video {
            min-height: 200px;
          }
        }
        /* Video controls overlay */
        .video-result-tile video::-webkit-media-controls {
          opacity: 0;
          transition: opacity 0.2s;
        }
        .video-result-tile:hover video::-webkit-media-controls {
          opacity: 1;
        }
      `;
      try { document.head.appendChild(vstyle); } catch (_) { }
    }
    if (!document.getElementById('puzzle-loader-styles')) {
      const style = document.createElement('style');
      style.id = 'puzzle-loader-styles';
      style.textContent = `
        .puzzle-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          grid-template-rows: repeat(3, 1fr);
          gap: 2px;
        }
        .puzzle-piece {
          background: linear-gradient(135deg, var(--primary) 0%, #8b5cf6 100%);
          border-radius: 2px;
          opacity: 0;
          transform: scale(0) rotate(0deg);
          animation: puzzlePop 1.2s ease-in-out infinite;
          animation-delay: var(--delay);
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
        }
        html[data-theme="light"] .puzzle-piece {
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
        }
        @keyframes puzzlePop {
          0%, 100% {
            opacity: 0;
            transform: scale(0) rotate(0deg);
          }
          50% {
            opacity: 1;
            transform: scale(1) rotate(180deg);
          }
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        .animate-fade-in-scale {
          animation: fadeInScale 0.3s ease-out;
        }
        @media (max-width: 480px) {
          .puzzle-grid { width: 80px !important; height: 80px !important; gap: 1.5px; }
        }
        @media (max-width: 375px) {
          .puzzle-grid { width: 72px !important; height: 72px !important; gap: 1px; }
        }
        @media (max-width: 320px) {
          .puzzle-grid { width: 64px !important; height: 64px !important; }
        }
      `;
      try { document.head.appendChild(style); } catch (_) { }
    }

    return tile;
  }

  setTileProgress(tile, pct, text) {
    try {
      // Throttle small progress updates to keep UI fast
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      const lastTs = tile._vt || 0;
      const lastPct = tile._vp || 0;
      const diffPct = Math.abs((pct || 0) - (lastPct || 0));
      if (!text && now - lastTs < 120 && diffPct < 3) return;
      tile._vt = now;
      tile._vp = pct;

      const statusEl = tile.querySelector('[data-role="tile-status"]');
      const txtEl = tile.querySelector('[data-role="tile-phase"]');

      // Update status text based on progress (parity with image loader)
      if (statusEl) {
        let nextText;
        if (pct < 20) nextText = 'Подготовка…';
        else if (pct < 40) nextText = 'Обработка…';
        else if (pct < 60) nextText = 'Генерация…';
        else if (pct < 80) nextText = 'Финализация…';
        else nextText = 'Почти готово…';
        if (statusEl.textContent !== nextText) statusEl.textContent = nextText;
      }

      if (txtEl && text && txtEl.textContent !== text) txtEl.textContent = text;

      // Animate puzzle pieces based on progress
      const pieces = tile.querySelectorAll('.puzzle-piece');
      const activePieces = Math.floor((pct / 100) * pieces.length);
      requestAnimationFrame(() => {
        pieces.forEach((piece, idx) => {
          if (idx < activePieces) {
            piece.style.opacity = '1';
            piece.style.transform = 'scale(1) rotate(0deg)';
          }
        });
      });
    } catch (_) { }
  }

  renderTileResult(tile, videoUrl, jobId, galleryId) {
    try { tile.setAttribute('data-status', 'done'); } catch (_) { }
    try { if (jobId) { tile.dataset.jobId = String(jobId); } } catch (_) { }
    // Сохраняем в персистентной очереди
    if (jobId && videoUrl) {
      this.addOrUpdateQueueEntry(jobId, { status: 'done', video_url: videoUrl, gallery_id: galleryId, completedAt: Date.now() });
    }

    // Обновляем баланс в реальном времени после успешной генерации
    try {
      if (window.balanceUpdater && typeof window.balanceUpdater.fetch === 'function') {
        window.balanceUpdater.fetch();
      }
    } catch (e) {
      console.log('[video-gen] Balance update skipped:', e.message);
    }

    // Keep frame unchanged; overlay aspect label and controls
    const arFromDataset = (tile.dataset && tile.dataset.aspectText) ? tile.dataset.aspectText : '';
    tile.innerHTML = `
      <div class="relative aspect-video bg-black group rounded-lg overflow-hidden">
        <div class="absolute top-2 left-2 z-10 flex flex-col gap-1">
          <div data-role="tile-aspect" class="px-2 py-1 rounded-full bg-black/60 text-white text-[10px] sm:text-xs font-medium backdrop-blur-sm">${this.escapeHtml(arFromDataset)}</div>
        </div>

        <!-- Видео без нативных controls -->
        <video class="video-player w-full h-full object-contain cursor-pointer"
               preload="auto"
               loop
               muted
               playsinline>
          Ваш браузер не поддерживает видео.
        </video>

        <!-- Кнопка Play по центру (компактная) - единственная кнопка управления воспроизведением -->
        <button type="button" class="video-play-btn absolute inset-0 flex items-center justify-center z-10 transition-opacity duration-200" style="opacity: 1;">
          <span class="play-btn-inner inline-flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-black/60 hover:bg-black/70 text-white shadow-lg backdrop-blur-sm transition transform hover:scale-110">
            <svg class="play-icon w-5 h-5 sm:w-6 sm:h-6 ml-0.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            <svg class="pause-icon w-5 h-5 sm:w-6 sm:h-6 hidden" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
            </svg>
          </span>
        </button>

        <!-- Кнопка открыть сверху справа -->
        <div class="absolute top-2 right-2 z-20">
          <a href="${videoUrl}" target="_blank" class="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-black/70 text-white hover:bg-black/80 transition flex items-center justify-center backdrop-blur-sm" aria-label="Открыть в новой вкладке">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>

        <!-- Маленький переключатель звука снизу справа -->
        <button type="button" class="volume-toggle-btn absolute bottom-2 right-2 z-20 w-8 h-8 rounded-full bg-black/60 hover:bg-black/70 text-white flex items-center justify-center transition" aria-label="Звук">
          <svg class="volume-icon-off w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <line x1="23" y1="9" x2="17" y2="15"/>
            <line x1="17" y1="9" x2="23" y2="15"/>
          </svg>
          <svg class="volume-icon-on w-4 h-4 hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
          </svg>
        </button>
      </div>
      <div class="p-2 sm:p-2.5 border-t border-[var(--bord)] bg-[var(--bg-card)]">
        <button type="button" class="persist-btn w-full px-3 py-2 rounded-lg bg-primary/90 hover:bg-primary focus:outline-none focus:ring-2 focus:ring-primary/30 text-white text-xs sm:text-sm font-medium transition" data-auth-text="Сохранить в профиле" data-guest-text="Добавить в мои обработки">${this.isAuthenticated ? 'Сохранить в профиле' : 'Добавить в мои обработки'}</button>
      </div>
    `;

    // Get video element
    let videoEl = null;
    try {
      videoEl = tile.querySelector('video.video-player');
    } catch (_) { }

    // Немедленно загружаем видео и устанавливаем src
    if (videoEl && videoUrl) {
      try {
        videoEl.src = videoUrl;
        videoEl.load();
      } catch (_) { }
    }

    // Download functionality removed for mobile optimization

    // Volume toggle functionality (simple mute/unmute button)
    try {
      const volumeToggle = tile.querySelector('.volume-toggle-btn');
      const volumeIconOn = tile.querySelector('.volume-icon-on');
      const volumeIconOff = tile.querySelector('.volume-icon-off');

      if (videoEl && volumeToggle) {
        // Video starts muted
        videoEl.muted = true;
        videoEl.volume = 0.7;

        // Toggle mute on click
        volumeToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          videoEl.muted = !videoEl.muted;
          if (volumeIconOn && volumeIconOff) {
            if (videoEl.muted) {
              volumeIconOn.classList.add('hidden');
              volumeIconOff.classList.remove('hidden');
            } else {
              volumeIconOn.classList.remove('hidden');
              volumeIconOff.classList.add('hidden');
            }
          }
        });
      }
    } catch (_) { }

    // Play/pause logic with centered button
    try {
      const playBtn = tile.querySelector('.video-play-btn');
      const playBtnInner = playBtn?.querySelector('.play-btn-inner');
      const playIcon = playBtn?.querySelector('.play-icon');
      const pauseIcon = playBtn?.querySelector('.pause-icon');

      if (videoEl && playBtn) {
        // Update button icons based on video state
        const updatePlayButton = () => {
          if (videoEl.paused) {
            if (playIcon) playIcon.classList.remove('hidden');
            if (pauseIcon) pauseIcon.classList.add('hidden');
            if (playBtnInner) playBtnInner.style.opacity = '1';
          } else {
            if (playIcon) playIcon.classList.add('hidden');
            if (pauseIcon) pauseIcon.classList.remove('hidden');
            // Hide button inner after short delay when playing
            setTimeout(() => {
              if (!videoEl.paused && playBtnInner) {
                playBtnInner.style.opacity = '0';
              }
            }, 1500);
          }
        };

        videoEl.addEventListener('play', updatePlayButton);
        videoEl.addEventListener('pause', updatePlayButton);
        videoEl.addEventListener('ended', updatePlayButton);

        // Show button on hover when playing
        tile.addEventListener('mouseenter', () => {
          if (playBtnInner) playBtnInner.style.opacity = '1';
        });
        tile.addEventListener('mouseleave', () => {
          if (!videoEl.paused && playBtnInner) {
            playBtnInner.style.opacity = '0';
          }
        });

        // Toggle play/pause on button click
        playBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          if (videoEl.paused) {
            const p = videoEl.play();
            if (p && typeof p.catch === 'function') {
              p.catch(() => { /* autoplay policy errors ignored */ });
            }
          } else {
            videoEl.pause();
          }
        });

        // Also toggle on video click
        videoEl.addEventListener('click', (e) => {
          e.stopPropagation();
          if (videoEl.paused) {
            const p = videoEl.play();
            if (p && typeof p.catch === 'function') {
              p.catch(() => { /* autoplay policy errors ignored */ });
            }
          } else {
            videoEl.pause();
          }
        });

        // Initial state
        updatePlayButton();
      }
    } catch (_) { }

    // Best-effort cache persisted/stream URL
    try { this.cacheAsset(videoUrl); } catch (_) { }

    // If already persisted earlier, lock the button state on render
    try {
      const pbtn = tile.querySelector('.persist-btn');
      if (pbtn && jobId && this.persistedJobs && this.persistedJobs.has(String(jobId))) {
        pbtn.textContent = this.isAuthenticated ? 'Сохранено в профиле' : 'Добавлено в обработки';
        pbtn.disabled = true;
        pbtn.classList.add('opacity-70', 'pointer-events-none');
      }
    } catch (_) { }

    // Try to refine aspect label from actual video metadata if available
    try {
      const arEl = tile.querySelector('[data-role="tile-aspect"]');
      if (videoEl && arEl) {
        const setFromMeta = () => {
          const vw = videoEl.videoWidth || 0;
          const vh = videoEl.videoHeight || 0;
          if (vw && vh) {
            const txt = this.computeAspectText(vw, vh);
            if (txt) arEl.textContent = txt;
          }
        };
        videoEl.addEventListener('loadedmetadata', setFromMeta, { once: true });
        // In case it was already loaded
        if (videoEl.readyState >= 1) setFromMeta();
      }
    } catch (_) { }
  }

  renderTileError(tile, message) {
    tile.innerHTML = `
      <div class="relative aspect-[16/9] bg-[var(--bg-card)] flex items-center justify-center">
        <div class="text-center p-4">
          <div class="text-red-500 font-semibold mb-1">Ошибка</div>
          <div class="text-xs sm:text-sm text-[var(--muted)]">${this.escapeHtml((message || 'Не удалось сгенерировать видео') + ' Токены не списаны.')}</div>
        </div>
      </div>
    `;
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
          <a href="/dashboard/my-jobs?tab=videos" class="video-action-btn secondary flex-1">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            Открыть в галерее
          </a>
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
      <div class="bg-[var(--bg-card)] rounded-2xl max-w-2xl w_full p-6 border border-[var(--bord)] shadow-2xl">
        <div class="flex items-center justify_between mb-4">
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
   * Настройка загрузки референсных изображений
   */
  setupReferenceUploads() {
    // T2V референс (одно фото)
    const t2vInput = document.getElementById('t2v-reference-images');
    const t2vRemoveBtn = document.getElementById('remove-t2v-reference');
    const t2vFileName = document.getElementById('t2v-file-name');

    if (t2vInput) {
      t2vInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          this.t2vReferenceFile = file;
          if (t2vFileName) t2vFileName.textContent = file.name;
          if (t2vRemoveBtn) t2vRemoveBtn.classList.remove('hidden');
        }
      });
    }

    if (t2vRemoveBtn) {
      t2vRemoveBtn.addEventListener('click', () => {
        this.t2vReferenceFile = null;
        if (t2vInput) t2vInput.value = '';
        if (t2vFileName) t2vFileName.textContent = 'Выбрать файл';
        t2vRemoveBtn.classList.add('hidden');
      });
    }

    // I2V source image (уже есть обработка в другом месте, но обновим кнопку удаления)
    const i2vRemoveBtn = document.getElementById('remove-video-image');
    const i2vFileName = document.getElementById('i2v-file-name');
    const i2vInput = document.getElementById('video-source-image');

    if (i2vInput) {
      i2vInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file && i2vFileName) {
          i2vFileName.textContent = file.name;
          if (i2vRemoveBtn) i2vRemoveBtn.classList.remove('hidden');
        }
      });
    }

    if (i2vRemoveBtn) {
      i2vRemoveBtn.addEventListener('click', () => {
        this.sourceImage = null;
        if (i2vInput) i2vInput.value = '';
        if (i2vFileName) i2vFileName.textContent = 'Выбрать файл';
        i2vRemoveBtn.classList.add('hidden');
      });
    }
  }

  /**
   * Обработка референсных файлов (DEPRECATED - не используется)
   */
  handleReferenceFiles(files, mode) {
    const maxFiles = 5;
    const maxSize = 10 * 1024 * 1024; // 10MB

    const fileArray = Array.from(files).filter(f => f.type.startsWith('image/'));

    if (fileArray.length === 0) {
      this.showError('Выберите изображения');
      return;
    }

    // Проверка лимита
    const currentCount = mode === 't2v' ? this.t2vReferenceFiles.length : 0;
    if (currentCount + fileArray.length > maxFiles) {
      this.showError(`Максимум ${maxFiles} изображений`);
      return;
    }

    // Проверка размера и добавление файлов
    for (const file of fileArray) {
      if (file.size > maxSize) {
        this.showError(`Файл ${file.name} слишком большой (макс. 10MB)`);
        continue;
      }

      if (mode === 't2v') {
        this.t2vReferenceFiles.push(file);
      }

      // Создаем превью
      this.createReferencePreview(file, mode);
    }
  }

  /**
   * Создание превью референсного изображения
   */
  createReferencePreview(file, mode) {
    const reader = new FileReader();

    reader.onload = (e) => {
      const containerId = mode === 't2v' ? 't2v-ref-previews' : 'video-ref-previews';
      const container = document.getElementById(containerId);

      if (!container) return;

      const previewDiv = document.createElement('div');
      previewDiv.className = 'relative group aspect-square rounded-lg overflow-hidden border-2 border-[var(--bord)] hover:border-primary/50 transition-colors';
      previewDiv.dataset.fileName = file.name;

      previewDiv.innerHTML = `
        <img src="${e.target.result}"
             alt="${file.name}"
             class="w-full h-full object-cover">
        <button type="button"
                class="ref-remove-btn absolute top-1 right-1 w-6 h-6 rounded-full bg-red-500 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center hover:bg-red-600"
                aria-label="Удалить">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm px-1.5 py-0.5">
          <p class="text-[9px] text-white truncate">${file.name}</p>
        </div>
      `;

      // Обработчик удаления
      const removeBtn = previewDiv.querySelector('.ref-remove-btn');
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeReferenceFile(file.name, mode);
        previewDiv.remove();
      });

      container.appendChild(previewDiv);
    };

    reader.readAsDataURL(file);
  }

  /**
   * Удаление референсного файла
   */
  removeReferenceFile(fileName, mode) {
    if (mode === 't2v') {
      this.t2vReferenceFiles = this.t2vReferenceFiles.filter(f => f.name !== fileName);
    }
  }

  /**
   * Обработка загрузки аудио файлов
   */
  handleAudioFiles(files) {
    const maxFiles = 3;
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowedTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm'];

    if (this.audioFiles.length >= maxFiles) {
      this.showError(`Максимум ${maxFiles} аудио файла`);
      return;
    }

    const filesArray = Array.from(files);
    for (const file of filesArray) {
      if (this.audioFiles.length >= maxFiles) break;

      // Validate type
      const isValidType = allowedTypes.includes(file.type) ||
                          file.name.match(/\.(mp3|wav|ogg|webm)$/i);
      if (!isValidType) {
        this.showError(`Файл ${file.name}: неподдерживаемый формат. Используйте MP3, WAV или OGG`);
        continue;
      }

      // Validate size
      if (file.size > maxSize) {
        this.showError(`Файл ${file.name}: размер превышает 50MB`);
        continue;
      }

      // Check duplicates
      if (this.audioFiles.some(f => f.name === file.name && f.size === file.size)) {
        this.showError(`Файл ${file.name} уже добавлен`);
        continue;
      }

      this.audioFiles.push(file);
      this.createAudioPreview(file);
    }
  }

  /**
   * Создание превью для аудио файла
   */
  createAudioPreview(file) {
    const container = document.getElementById('audio-previews');
    if (!container) return;

    const preview = document.createElement('div');
    preview.className = 'flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--bord)]';
    preview.dataset.fileName = file.name;

    const icon = `
      <div class="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-green-500/20 to-green-500/5 flex items-center justify-center">
        <svg class="w-5 h-5 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
        </svg>
      </div>
    `;

    const info = `
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-[var(--text)] truncate">${file.name}</p>
        <p class="text-xs text-[var(--muted)]">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
      </div>
    `;

    const removeBtn = `
      <button type="button" class="flex-shrink-0 p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-colors">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    `;

    preview.innerHTML = icon + info + removeBtn;

    const btn = preview.querySelector('button');
    btn.addEventListener('click', () => {
      this.removeAudioFile(file.name);
    });

    container.appendChild(preview);
  }

  /**
   * Удаление аудио файла
   */
  removeAudioFile(fileName) {
    this.audioFiles = this.audioFiles.filter(f => f.name !== fileName);
    const container = document.getElementById('audio-previews');
    if (container) {
      const preview = container.querySelector(`[data-file-name="${fileName}"]`);
      if (preview) preview.remove();
    }
  }

  /**
   * Обновление секции референсов и аудио в зависимости от режима и модели
   */
  updateReferenceSection() {
    const i2vSection = document.getElementById('i2v-upload-compact');
    const t2vSection = document.getElementById('t2v-references-section');

    console.log('updateReferenceSection called:', {
      mode: this.currentMode,
      selectedModel: this.selectedModel?.model_id
    });

    if (this.currentMode === 'i2v') {
      // I2V: показываем секцию исходного фото
      if (i2vSection) i2vSection.style.display = 'block';
      if (t2vSection) t2vSection.style.display = 'none';
    } else {
      // T2V: показываем секцию референсных изображений
      if (i2vSection) i2vSection.style.display = 'none';
      if (t2vSection) {
        // Показываем только если модель поддерживает frameImages
        const show = this.selectedModel && this.currentModelSupportsFrameImages();
        t2vSection.style.display = show ? 'block' : 'none';
      }
    }
  }

  /**
   * Проверка поддержки frameImages текущей моделью
   */
  currentModelSupportsFrameImages() {
    if (!this.selectedModel || !this.selectedModel.model_id) return false;

    // Проверяем по supported_references если есть
    if (this.selectedModel.supported_references) {
      return this.selectedModel.supported_references.includes('frameImages');
    }

    // Иначе проверяем по известным провайдерам
    const modelId = String(this.selectedModel.model_id).toLowerCase();
    return modelId.includes('bytedance') ||
           modelId.includes('kling') ||
           modelId.includes('vidu') ||
           modelId.includes('runway') ||
           modelId.includes('sora');
  }

  /**
   * Проверка поддержки audioInputs текущей моделью
   */
  currentModelSupportsAudio() {
    if (!this.selectedModel) return false;

    // Проверяем по supported_references если есть
    if (this.selectedModel.supported_references && Array.isArray(this.selectedModel.supported_references)) {
      const hasAudioInputs = this.selectedModel.supported_references.includes('audioInputs');
      console.log('Audio support check:', {
        model: this.selectedModel.model_id,
        supported_references: this.selectedModel.supported_references,
        hasAudioInputs: hasAudioInputs
      });
      return hasAudioInputs;
    }

    // Fallback: некоторые провайдеры поддерживают аудио по умолчанию
    if (this.selectedModel.model_id) {
      const modelId = String(this.selectedModel.model_id).toLowerCase();
      const fallbackSupport = modelId.includes('vidu') ||
                              modelId.includes('pixverse') ||
                              modelId.includes('runway') ||
                              modelId.includes('kling');
      if (fallbackSupport) {
        console.log('Audio support via fallback for:', this.selectedModel.model_id);
      }
      return fallbackSupport;
    }

    return false;
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

  // Небольшой helper для паузы между отправками запросов
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Инициализация при загрузке страницы
 * Раньше модуль инициализировался только если есть #video-generation-form.
 * Теперь также инициализируемся на страницах галереи с кнопкой очистки или гридом результатов.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Инициализируем модуль ТОЛЬКО в видеорежиме, чтобы не вешать страницу в режиме изображений.
  const isVideoMode =
    document.documentElement.classList.contains('mode-video') ||
    (new URLSearchParams(window.location.search).get('type') === 'video') ||
    (function () { try { return localStorage.getItem('gen.topMode') === 'video'; } catch (_) { return false; } })();

  let initDone = false;
  function bootVideoModule() {
    if (initDone) return;
    window.videoGeneration = new VideoGeneration();
    initDone = true;
    console.log('Модуль генерации видео инициализирован');
  }

  if (isVideoMode) {
    bootVideoModule();
  } else {
    // Отложенная инициализация: когда пользователь переключится на видео
    document.addEventListener('videoModeChanged', () => bootVideoModule(), { once: true });
    // На случай прямого клика по табу "Видео" без кастомного события
    const videoTab = document.querySelector('.generation-mode-tab[data-mode="video"]');
    if (videoTab) {
      videoTab.addEventListener('click', () => bootVideoModule(), { once: true });
    }
  }
});
