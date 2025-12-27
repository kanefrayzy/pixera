// Video Prompts & Showcase Management
(function() {
  const IS_STAFF = (document.getElementById('gen-root')?.dataset.isStaff || 'false') === 'true';
  let currentMode = 't2v';
  let categoriesLoaded = false;

  function syncAdminModeSelect() {
    const sel = document.getElementById('vpcMode');
    if (sel) {
      const m = getCurrentVideoMode();
      if (m) sel.value = m;
    }
  }

  function getCurrentVideoMode() {
    const activeTab = document.querySelector('.video-source-tab.active');
    return activeTab ? activeTab.dataset.source : 't2v';
  }

  function getCSRF() {
    const input = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
    if (input) return input;
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  async function postFD(url, fd) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCSRF(), 'X-Requested-With': 'fetch' },
      body: fd,
      credentials: 'same-origin'
    });
    let j = {};
    const ctype = (r.headers.get('content-type') || '').toLowerCase();
    if (ctype.includes('application/json')) {
      try { j = await r.json(); } catch(_) { j = {}; }
    } else {
      try { const t = await r.text(); j = { ok: r.ok, error: (t || '').slice(0, 300) }; } catch(_) { j = {}; }
    }
    if (r.redirected) {
      const to = r.url || '';
      if (to.includes('/accounts/login') || to.includes('/admin/login')) {
        throw new Error('Требуется вход. Войдите под staff (админ) и повторите действие.');
      }
    }
    if (r.status === 403) throw new Error(j.error || 'Недостаточно прав (нужен staff) или CSRF-токен недействителен.');
    if (r.status === 400) throw new Error(j.error || 'Неверные данные формы. Проверьте поля.');
    if (!r.ok || j.ok === false || j.success === false) throw new Error(j.error || ('Ошибка ' + r.status));
    return j;
  }

  async function postJSON(url, data) {
    const fd = new FormData();
    Object.entries(data || {}).forEach(([k, v]) => fd.append(k, v));
    return postFD(url, fd);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Expand "All categories" section if needed (video)
  function expandAllVideoCategories() {
    const btn = document.getElementById('showAllVideoCategoriesBtn');
    const sec = document.getElementById('allVideoCategoriesSection');
    if (sec && sec.classList.contains('hidden') && btn) {
      try { btn.click(); } catch(_) {}
    }
  }

  // Progressive "Show more" for video categories — 3 rows initially, responsive
  function setupShowMoreVideoCategories() {
    const container = document.getElementById('videoCategoriesContainer');
    if (!container) return;
    const compact = container.querySelector('.categories-grid-compact');
    const fullSection = document.getElementById('allVideoCategoriesSection');
    const full = fullSection ? fullSection.querySelector('.categories-grid-full') : null;

    if (!compact) return;

    // Remove "Show all" button if present
    const showAllBtn = document.getElementById('showAllVideoCategoriesBtn');
    try { showAllBtn?.remove(); } catch(_) {}

    // Merge all cards into a single grid (move from full -> compact)
    if (fullSection) {
      if (full) {
        full.querySelectorAll('.category-card-compact').forEach(c => {
          if (!c.classList.contains('category-show-all')) compact.appendChild(c);
        });
      }
      fullSection.remove();
    }

    // Create "Show more" button
    let btn = document.getElementById('vpcShowMore');
    if (!btn) {
      btn = document.createElement('button');
      btn.id = 'vpcShowMore';
      btn.type = 'button';
      btn.className = 'btn btn-ghost w-full mt-4 text-sm';
      btn.innerHTML = '<span>Показать ещё</span>';
      compact.parentElement.appendChild(btn);
    }

    function getCols() {
      const cs = getComputedStyle(compact);
      const cols = (cs.gridTemplateColumns || '').split(' ').filter(Boolean).length || 3;
      return Math.max(1, cols);
    }

    let extraRows = 0;

    function update() {
      const cols = getCols();
      const base = 3 * cols; // show 3 rows initially
      const visible = base + extraRows * cols;
      const cards = Array.from(compact.querySelectorAll('.category-card-compact'));
      let shown = 0;
      cards.forEach(card => {
        const hide = shown >= visible;
        card.classList.toggle('hidden', hide);
        if (!hide) shown += 1;
      });
      btn.style.display = shown >= cards.length ? 'none' : '';
    }

    update();
    btn.addEventListener('click', () => { extraRows += 1; update(); });
    window.addEventListener('resize', () => { update(); });
  }

  // Highlight category card by exact name (case-insensitive)
  function highlightVideoCategoryByName(name) {
    if (!name) return;
    const target = (name || '').trim().toLowerCase();
    setTimeout(() => {
      const container = document.getElementById('videoCategoriesContainer');
      if (!container) return;
      let card = null;
      container.querySelectorAll('.category-card-compact').forEach(c => {
        if (!card) {
          const nm = (c.dataset.name || '').trim().toLowerCase();
          if (nm === target) card = c;
        }
      });
      if (!card) {
        // Try progressive reveal via "Показать ещё"
        const tryReveal = () => {
          const moreBtn = document.getElementById('vpcShowMore');
          if (moreBtn && moreBtn.style.display !== 'none') {
            try { moreBtn.click(); } catch(_) {}
            return true;
          }
          return false;
        };
        // Attempt a few times to reveal more rows
        let attempts = 0;
        const timer = setInterval(() => {
          attempts += 1;
          if (tryReveal() === false || attempts > 10) {
            clearInterval(timer);
            // Fallback: legacy expand-all (noop if removed)
            expandAllVideoCategories();
            setTimeout(() => highlightVideoCategoryByName(name), 250);
          } else {
            // After revealing, retry finding card
            const cardsNow = container.querySelectorAll('.category-card-compact');
            let found = null;
            cardsNow.forEach(c => {
              if (!found) {
                const nm2 = (c.dataset.name || '').trim().toLowerCase();
                if (nm2 === target) found = c;
              }
            });
            if (found) {
              clearInterval(timer);
              try {
                found.style.outline = '2px solid var(--primary)';
                found.style.outlineOffset = '2px';
                found.scrollIntoView({ behavior: 'smooth', block: 'center' });
                setTimeout(() => { found.style.outline = ''; }, 2000);
              } catch(_) {}
            }
          }
        }, 150);
        return;
      }
      try {
        card.style.outline = '2px solid var(--primary)';
        card.style.outlineOffset = '2px';
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => { card.style.outline = ''; }, 2000);
      } catch(_) {}
    }, 200);
  }

  // Load categories
  async function loadVideoCategories(mode) {
    const container = document.getElementById('videoCategoriesContainer');
    if (!container) return;

    // Skip if already loading or loaded for same mode
    if (container.dataset.loading === 'true') return;
    container.dataset.loading = 'true';

    container.innerHTML = '<p class="text-center text-muted">Загрузка категорий...</p>';

    try {
      const response = await fetch(`/generate/api/video/categories/?mode=${mode}`);
      const data = await response.json();
      categoriesLoaded = true;

      if (data.categories && data.categories.length > 0) {
        const cats = data.categories;
        const firstFive = cats.slice(0, 5);
        const rest = cats.slice(5);

        let html = '<div class="categories-grid-compact">';

        firstFive.forEach(cat => {
          html += `
            <div class="category-card-compact" data-category-id="${cat.id}" data-name="${escapeHtml(cat.name)}" data-desc="${escapeHtml(cat.description||'')}" data-order="${cat.order||0}" data-active="${cat.is_active?'1':'0'}" data-image-url="${cat.image_url||''}">
              <div class="category-image-wrapper-compact">
                ${cat.image_url ? `<img src="${cat.image_url}" alt="${escapeHtml(cat.name)}" class="category-image-compact" loading="lazy">` : ''}
                <div class="category-overlay-compact"></div>
                <h3 class="category-name-compact">${escapeHtml(cat.name)}</h3>
                ${IS_STAFF ? `
                  <div class="pc-card-actions">
                    <button class="pc-btn pc-edit" type="button" title="Редактировать" data-id="${cat.id}">✎</button>
                    <button class="pc-btn pc-del" type="button" title="Удалить" data-id="${cat.id}">✕</button>
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        });

        if (rest.length > 0) {
          html += `
            <button type="button" id="showAllVideoCategoriesBtn" class="category-card-compact category-show-all">
              <div class="category-image-wrapper-compact">
                <div class="show-all-content">
                  <svg class="show-all-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                  <span class="show-all-text">Все категории</span>
                  <span class="show-all-count">${cats.length}</span>
                </div>
              </div>
            </button>
          `;
        }

        html += '</div>';

        if (rest.length > 0) {
          html += '<div id="allVideoCategoriesSection" class="hidden mt-6"><div class="categories-grid-full">';
          rest.forEach(cat => {
            html += `
              <div class="category-card-compact" data-category-id="${cat.id}" data-name="${escapeHtml(cat.name)}" data-desc="${escapeHtml(cat.description||'')}" data-order="${cat.order||0}" data-active="${cat.is_active?'1':'0'}" data-image-url="${cat.image_url||''}">
                <div class="category-image-wrapper-compact">
                  ${cat.image_url ? `<img src="${cat.image_url}" alt="${escapeHtml(cat.name)}" class="category-image-compact" loading="lazy">` : ''}
                  <div class="category-overlay-compact"></div>
                  <h3 class="category-name-compact">${escapeHtml(cat.name)}</h3>
                  ${IS_STAFF ? `
                    <div class="pc-card-actions">
                      <button class="pc-btn pc-edit" type="button" title="Редактировать" data-id="${cat.id}">✎</button>
                      <button class="pc-btn pc-del" type="button" title="Удалить" data-id="${cat.id}">✕</button>
                    </div>
                  ` : ''}
                </div>
              </div>
            `;
          });
          html += '</div></div>';
        }

        container.innerHTML = html;
        container.dataset.loading = 'false';
        attachCategoryHandlers();
        // Enforce "3 rows + Show more" UX for video categories
        setupShowMoreVideoCategories();
      } else {
        container.innerHTML = '<p class="text-center text-muted">Категории не найдены</p>';
        container.dataset.loading = 'false';
      }
    } catch (error) {
      container.innerHTML = '<p class="text-center text-red-500">Ошибка загрузки категорий</p>';
      container.dataset.loading = 'false';
    }
  }

  // Load showcase
  async function loadVideoShowcase(mode) {
    const container = document.getElementById('videoShowcaseContainer');
    if (!container) return;

    container.innerHTML = '<p class="text-center text-muted col-span-full">Загрузка примеров...</p>';

    try {
      const response = await fetch(`/generate/api/video/showcase/?mode=${mode}`);
      const data = await response.json();

      if (data.examples && data.examples.length > 0) {
        container.innerHTML = data.examples.map(video => `
          <div class="showcase-item">
            <div class="showcase-media">
              <video
                class="showcase-video w-full h-full object-cover cursor-pointer transition-all duration-300"
                src="${video.video_url}"
                poster="${video.thumbnail_url || ''}"
                preload="metadata"
                playsinline
                muted
                loop
                title="${escapeHtml(video.title)}"
                loading="lazy"
              ></video>
              <!-- Volume control (shows only if audio is present) -->
              <div class="showcase-vol-wrap absolute right-2 top-2 items-center gap-2 bg-black/55 text-white px-2 py-1.5 rounded-xl backdrop-blur-sm z-20">
                <button type="button" class="showcase-mute-btn" aria-label="Звук">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5 9v6h4l5 5V4L9 9H5z"></path>
                  </svg>
                </button>
                <input type="range" class="showcase-volume w-20 sm:w-24 accent-[var(--primary)]" min="0" max="100" value="0">
              </div>
              <!-- No-audio badge -->
              <div class="showcase-noaudio absolute right-2 top-2 hidden items-center gap-2 bg-black/55 text-white px-2 py-1.5 rounded-xl backdrop-blur-sm z-20" title="Нет звука">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M16.5 12a4.5 4.5 0 01-1.1 2.9l1.1 1.1A6 6 0 0018 12a5.9 5.9 0 00-.6-2.6l-1.1 1.1c.12.48.2.98.2 1.5zM19 5l-1.5 1.5-2.1 2.1L12 12l-3 3H5v-6h3l3-3 2.1-2.1L17.5 3 19 4.5zM4 4l16 16-1.5 1.5L2.5 5.5 4 4z"></path>
                </svg>
                <span class="text-xs">Нет звука</span>
              </div>
              <button class="video-play-btn" aria-label="Воспроизвести видео" title="Воспроизвести">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="28" height="28">
                  <path d="M8 5v14l11-7z" fill="currentColor"></path>
                </svg>
              </button>
            </div>
            <div class="showcase-content">
              <h3 class="showcase-title">${escapeHtml(video.title)}</h3>
              ${video.prompt && video.prompt.trim()
                ? `
                <div class="showcase-prompt-header" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9h8M8 13h5M4 6h16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2z"></path>
                  </svg>
                  <span>Промпт</span>
                </div>
                <div class="showcase-prompt-box">
                  <p class="showcase-prompt">${escapeHtml(video.prompt)}</p>
                </div>
                `
                : ''
              }
              <button class="showcase-use-btn" data-prompt="${escapeHtml(video.prompt || '')}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                </svg>
                <span>Использовать промпт</span>
              </button>
            </div>
          </div>
        `).join('');

        attachShowcaseHandlers();
      } else {
        container.innerHTML = '<p class="text-center text-muted col-span-full">Примеры не найдены</p>';
      }
    } catch (error) {
      container.innerHTML = '<p class="text-center text-red-500 col-span-full">Ошибка загрузки примеров</p>';
    }
  }

  function attachCategoryHandlers() {
    // Show all button
    document.getElementById('showAllVideoCategoriesBtn')?.addEventListener('click', function() {
      const section = document.getElementById('allVideoCategoriesSection');
      if (section) {
        const isHidden = section.classList.contains('hidden');
        section.classList.toggle('hidden');
        const text = this.querySelector('.show-all-text');
        const icon = this.querySelector('.show-all-icon');
        if (text) text.textContent = isHidden ? 'Скрыть' : 'Все категории';
        if (icon) {
          icon.innerHTML = isHidden
            ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>'
            : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>';
        }
      }
    });

    // Category clicks
    document.querySelectorAll('.category-card-compact:not(.category-show-all)').forEach(card => {
      card.addEventListener('click', async function(e) {
        if (e.target.closest('.pc-card-actions')) return;

        const categoryId = this.dataset.categoryId;
        if (!categoryId) return;

        const categoryName = this.querySelector('.category-name-compact').textContent;
        openVideoPromptModal(categoryId, categoryName);
      });
    });

    // Admin buttons
    if (IS_STAFF) {
      document.querySelectorAll('.pc-edit').forEach(btn => {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          const card = this.closest('.category-card-compact');
          openEditModal(card);
        });
      });

      document.querySelectorAll('.pc-del').forEach(btn => {
        btn.addEventListener('click', async function(e) {
          e.stopPropagation();
          const id = this.dataset.id;
          if (!confirm('Удалить категорию?')) return;
          try {
            await postJSON(`/generate/api/video/categories/${id}/delete/`, {});
            location.reload();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
      });
    }
  }

  function attachShowcaseHandlers() {
    // Video UX: overlay play button + click/hover control
    document.querySelectorAll('.showcase-video').forEach(video => {
      const overlay = video.parentElement.querySelector('.video-play-btn');
      const showOverlay = () => { if (overlay) overlay.style.display = 'flex'; };
      const hideOverlay = () => { if (overlay) overlay.style.display = 'none'; };

      // Toggle on click
      video.addEventListener('click', () => {
        try { video.paused ? video.play() : video.pause(); } catch(_) {}
      });
      // Try autoplay on hover (muted, playsinline)
      video.addEventListener('mouseenter', () => {
        try { if (video.paused) video.play(); } catch(_) {}
      });

      // Sync overlay with state
      video.addEventListener('play', hideOverlay);
      video.addEventListener('pause', showOverlay);

      // Initial overlay state
      if (video.paused) showOverlay(); else hideOverlay();

      // Overlay click to play
      if (overlay) {
        overlay.addEventListener('click', (e) => {
          e.preventDefault(); e.stopPropagation();
          try { video.play(); } catch(_) {}
          hideOverlay();
        });
      }

      // Volume controls per video (adaptive, theme-aware)
      const volWrap = video.parentElement.querySelector('.showcase-vol-wrap');
      const noAudioWrap = video.parentElement.querySelector('.showcase-noaudio');
      const vol = video.parentElement.querySelector('.showcase-volume');
      const muteBtn = video.parentElement.querySelector('.showcase-mute-btn');

      function setVolume(v) {
        const val = Math.max(0, Math.min(100, v|0));
        video.volume = val / 100;
        video.muted = val === 0;
      }

      if (vol) {
        vol.addEventListener('input', (e) => {
          const val = parseInt(e.target.value || '0', 10);
          setVolume(val);
        });
      }

      if (muteBtn) {
        muteBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          if (video.muted || video.volume === 0) {
            setVolume(40);
            if (vol) vol.value = 40;
          } else {
            setVolume(0);
            if (vol) vol.value = 0;
          }
        });
      }

      function detectHasAudio() {
        try {
          let detectedTrue = false;
          let detectedFalse = false;

          // Firefox
          if (typeof video.mozHasAudio !== 'undefined') {
            if (video.mozHasAudio) detectedTrue = true;
            else detectedFalse = true;
          }

          // Chromium/WebKit heuristic (becomes >0 only after decoding)
          if (typeof video.webkitAudioDecodedByteCount !== 'undefined') {
            if (video.webkitAudioDecodedByteCount > 0) detectedTrue = true;
          }

          // Safari/Chrome audioTracks (sometimes filled later)
          if (video.audioTracks && typeof video.audioTracks.length === 'number') {
            if (video.audioTracks.length > 0) detectedTrue = true;
            else detectedFalse = detectedFalse || true;
          }

          // Prefer not to hide controls on uncertainty
          const showControls = detectedTrue || !detectedFalse;
          if (volWrap) volWrap.classList.toggle('hidden', !showControls);
          if (noAudioWrap) noAudioWrap.classList.toggle('hidden', showControls);
        } catch (_) {
          // On any error — show controls to avoid false "Нет звука"
          if (volWrap) volWrap.classList.remove('hidden');
          if (noAudioWrap) noAudioWrap.classList.add('hidden');
        }
      }

      // Initial volume for autoplay policy + audio detection
      setVolume(0);
      if (vol) vol.value = 0;
      detectHasAudio();
      video.addEventListener('loadedmetadata', detectHasAudio, { once: true });
      video.addEventListener('loadeddata', detectHasAudio, { once: true });
      video.addEventListener('canplay', detectHasAudio, { once: true });
      video.addEventListener('timeupdate', detectHasAudio, { once: true });
    });

    // Use prompt buttons
    document.querySelectorAll('.showcase-use-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const prompt = this.dataset.prompt;
        const promptField = document.getElementById('video-prompt');
        if (promptField) {
          promptField.value = prompt;
          promptField.focus();

          const originalHTML = this.innerHTML;
          this.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            <span>Добавлено!</span>
          `;
          this.classList.add('success');

          setTimeout(() => {
            this.innerHTML = originalHTML;
            this.classList.remove('success');
          }, 2000);
        }
      });
    });
  }

  async function openVideoPromptModal(categoryId, categoryName) {
    const modal = document.getElementById('videoPromptCategoryModal');
    const modalTitle = document.getElementById('videoModalCategoryTitle');
    const modalContainer = document.getElementById('videoModalPromptsContainer');

    if (!modal || !modalTitle || !modalContainer) return;

    modalTitle.textContent = categoryName;
    modalContainer.innerHTML = '<div class="text-center text-[var(--muted)] py-8">Загрузка...</div>';
    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    try {
      const response = await fetch(`/generate/api/video/categories/${categoryId}/prompts`);
      const data = await response.json();

      const adminCreate = IS_STAFF ? `
        <div class="p-3 mb-3 rounded-xl border border-[var(--bord)] bg-black/[.03]">
          <div class="grid gap-2 sm:grid-cols-2">
            <input id="vcpTitle" class="field" type="text" placeholder="Заголовок" maxlength="150">
            <input id="vcpOrder" class="field" type="number" placeholder="Порядок" value="0">
            <select id="vcpSubcat" class="field">
              <option value="">Без подкатегории</option>
            </select>
            <textarea id="vcpText" class="field sm:col-span-2" rows="3" placeholder="Текст промпта"></textarea>
            <textarea id="vcpEn" class="field sm:col-span-2" rows="3" placeholder="Английский промпт"></textarea>
            <label class="pc-inline"><input id="vcpActive" type="checkbox" checked><span>Активен</span></label>
            <button id="vcpCreateBtn" class="btn btn-primary" type="button">+ Промпт</button>
          </div>
          <div class="mt-3 rounded-lg border border-[var(--bord)] p-3">
            <div class="text-xs text-[var(--muted)] mb-2">Подкатегории (админ)</div>
            <div class="grid gap-2 sm:grid-cols-3">
              <input id="vscName" class="field" type="text" placeholder="Название подкатегории" maxlength="120">
              <input id="vscOrder" class="field" type="number" placeholder="Порядок" value="0">
              <label class="pc-inline"><input id="vscActive" type="checkbox" checked><span>Активна</span></label>
            </div>
            <div class="mt-2 flex justify-end">
              <button id="vscCreateBtn" class="btn btn-ghost" type="button">+ Подкатегория</button>
            </div>
          </div>
        </div>
      ` : '';

      const items = (data.prompts || []).map(prompt => `
        <div class="prompt-item-modal" data-id="${prompt.id}" data-prompt="${escapeHtml(prompt.prompt_text)}" data-prompt-en="${escapeHtml(prompt.prompt_en||'')}" data-order="${prompt.order||0}" data-active="${prompt.is_active?'1':'0'}">
          <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 items-start">
            <p class="text-sm text-[var(--muted)] leading-relaxed flex-1 min-w-0">${escapeHtml(prompt.prompt_text)}</p>
            <div class="flex items-center gap-2">
              ${IS_STAFF ? `<button class="btn btn-ghost text-xs js-vcp-edit" type="button">Редактировать</button><button class="btn btn-ghost text-xs js-vcp-del" type="button">Удалить</button>` : ''}
              <button class="btn btn-primary shrink-0 w-full sm:w-auto js-use-btn">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
                Использовать
              </button>
            </div>
          </div>
        </div>
      `).join('');

      modalContainer.innerHTML = `
        ${adminCreate}
        <div id="vpg-subcats" class="flex flex-wrap gap-2 mb-3"></div>
        <div id="vpg-items" class="space-y-3">${items || '<div class="text-center text-[var(--muted)] py-8">Промпты не найдены</div>'}</div>
      `;

      // Helpers to bind "Use" buttons (for dynamic lists)
      function bindVideoUseButtons(rootEl) {
        rootEl.querySelectorAll('.js-use-btn').forEach(btn => {
          btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const promptItem = this.closest('.prompt-item-modal');
            const promptTextEn = promptItem?.dataset.promptEn;
            const promptTextRu = promptItem?.dataset.prompt;
            const promptToUse = promptTextEn && promptTextEn.trim() !== '' ? promptTextEn : promptTextRu;

            const promptField = document.getElementById('video-prompt');
            if (promptField) {
              promptField.value = promptToUse || '';
              promptField.focus();
            }

            const originalHTML = this.innerHTML;
            this.innerHTML = `
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              Скопировано!
            `;
            this.classList.add('copied');

            setTimeout(() => {
              this.innerHTML = originalHTML;
              this.classList.remove('copied');
            }, 2000);

            closeVideoPromptModal();
          });
        });
      }

      // Load and render subcategories for VIDEO (pills + fill select)
      async function loadVideoSubcategories() {
        try {
          const r = await fetch(`/generate/api/video/categories/${categoryId}/subcategories`);
          const j = await r.json();
          const wrap = modalContainer.querySelector('#vpg-subcats');
          const itemsWrap = modalContainer.querySelector('#vpg-items');
          if (!wrap) return;

          const subs = (j.subcategories || []);

          // Fill select for prompt creation
          const sel = modalContainer.querySelector('#vcpSubcat');
          if (sel) {
            sel.innerHTML = `<option value="">Без подкатегории</option>` + subs.map(sc => `<option value="${sc.id}">${escapeHtml(sc.name)}</option>`).join('');
          }

          // Render pills
          const pills = [];
          pills.push(`<button type="button" class="px-3 py-1.5 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] text-xs sm:text-sm vpg-subpill" data-id="">Все</button>`);
          subs.forEach(sc => {
            pills.push(`<button type="button" class="px-3 py-1.5 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary/60 hover:text-primary text-xs sm:text-sm vpg-subpill" data-id="${sc.id}">${escapeHtml(sc.name)} <span class="text-[var(--muted)]">(${sc.prompts_count})</span></button>`);
          });
          wrap.innerHTML = pills.join('');

          // Bind pill clicks
          wrap.querySelectorAll('.vpg-subpill').forEach(btn => {
            btn.addEventListener('click', async () => {
              const subId = btn.dataset.id || '';
              wrap.querySelectorAll('.vpg-subpill').forEach(b => b.classList.remove('bg-primary/15','text-primary','border-primary/30'));
              if (subId === '') {
                btn.classList.add('bg-primary/15','text-primary','border-primary/30');
                // Reset to category-wide prompts (preloaded)
                itemsWrap.innerHTML = `
                  ${ (data.prompts || []).map(prompt => `
                    <div class="prompt-item-modal" data-id="${prompt.id}" data-prompt="${escapeHtml(prompt.prompt_text)}" data-prompt-en="${escapeHtml(prompt.prompt_en||'')}" data-order="${prompt.order||0}" data-active="${prompt.is_active?'1':'0'}">
                      <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 items-start">
                        <p class="text-sm text-[var(--muted)] leading-relaxed flex-1 min-w-0">${escapeHtml(prompt.prompt_text)}</p>
                        <div class="flex items-center gap-2">
                          ${IS_STAFF ? `<button class="btn btn-ghost text-xs js-vcp-edit" type="button">Редактировать</button><button class="btn btn-ghost text-xs js-vcp-del" type="button">Удалить</button>` : ''}
                          <button class="btn btn-primary shrink-0 w-full sm:w-auto js-use-btn">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                            Использовать
                          </button>
                        </div>
                      </div>
                    </div>
                  `).join('') }
                `;
                bindVideoUseButtons(itemsWrap);
              } else {
                try {
                  const r2 = await fetch(`/generate/api/video/subcategories/${subId}/prompts`);
                  const j2 = await r2.json();
                  const dataItems = (j2.prompts || []);
                  const itemsHtml = dataItems.map(prompt => `
                    <div class="prompt-item-modal" data-id="${prompt.id}" data-prompt="${escapeHtml(prompt.prompt_text)}" data-prompt-en="${escapeHtml(prompt.prompt_en||'')}" data-order="${prompt.order||0}" data-active="${prompt.is_active?'1':'0'}">
                      <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 items-start">
                        <p class="text-sm text-[var(--muted)] leading-relaxed flex-1 min-w-0">${escapeHtml(prompt.prompt_text)}</p>
                        <div class="flex items-center gap-2">
                          ${IS_STAFF ? `<button class="btn btn-ghost text-xs js-vcp-edit" type="button">Редактировать</button><button class="btn btn-ghost text-xs js-vcp-del" type="button">Удалить</button>` : ''}
                          <button class="btn btn-primary shrink-0 w-full sm:w-auto js-use-btn">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                            Использовать
                          </button>
                        </div>
                      </div>
                    </div>
                  `).join('');
                  itemsWrap.innerHTML = itemsHtml || '<div class="text-center text-[var(--muted)] py-8">Промпты не найдены</div>';
                  bindVideoUseButtons(itemsWrap);
                  btn.classList.add('bg-primary/15','text-primary','border-primary/30');
                } catch (e) {
                  itemsWrap.innerHTML = '<div class="text-center text-red-500 py-8">Ошибка загрузки подкатегории</div>';
                }
              }
            });
          });

          // Admin: create subcategory
          modalContainer.querySelector('#vscCreateBtn')?.addEventListener('click', async () => {
            const name = (modalContainer.querySelector('#vscName')?.value || '').trim();
            const order = modalContainer.querySelector('#vscOrder')?.value || '0';
            const active = modalContainer.querySelector('#vscActive')?.checked ? '1' : '0';
            if (!name) { alert('Введите название подкатегории'); return; }
            try {
              await postJSON('/generate/api/video/subcategories/create', { category_id: categoryId, name, order, is_active: active });
              await loadVideoSubcategories();
              (modalContainer.querySelector('#vscName') || {}).value = '';
              (modalContainer.querySelector('#vscOrder') || {}).value = '0';
            } catch (e) { alert(e.message || String(e)); }
          });

          // Default select "Все"
          const first = wrap.querySelector('.vpg-subpill[data-id=""]');
          if (first) first.click();
        } catch (e) {
          // silent
        }
      }

      // Boot subcategories UI
      loadVideoSubcategories();

      // Create prompt
      if (IS_STAFF) {
        modalContainer.querySelector('#vcpCreateBtn')?.addEventListener('click', async () => {
          const title = (modalContainer.querySelector('#vcpTitle')?.value || '').trim();
          const text = (modalContainer.querySelector('#vcpText')?.value || '').trim();
          const en = (modalContainer.querySelector('#vcpEn')?.value || '').trim();
          const order = modalContainer.querySelector('#vcpOrder')?.value || '0';
          const active = modalContainer.querySelector('#vcpActive')?.checked ? '1' : '0';
          if (!title || !text) { alert('Заполните заголовок и текст'); return; }
          try {
            const subSel = modalContainer.querySelector('#vcpSubcat');
            const subcategory_id = (subSel && subSel.value) ? subSel.value : '';
            await postJSON('/generate/api/video/prompts/create/', { category_id: categoryId, subcategory_id, title, prompt_text: text, prompt_en: en, order, is_active: active });
            location.reload();
          } catch (e) { alert(e.message || String(e)); }
        });
      }

      // Use buttons
      modalContainer.querySelectorAll('.js-use-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          const promptItem = this.closest('.prompt-item-modal');
          const promptTextEn = promptItem.dataset.promptEn;
          const promptTextRu = promptItem.dataset.prompt;
          const promptToUse = promptTextEn && promptTextEn.trim() !== '' ? promptTextEn : promptTextRu;

          const promptField = document.getElementById('video-prompt');
          if (promptField) {
            promptField.value = promptToUse;
            promptField.focus();
          }

          const originalHTML = this.innerHTML;
          this.innerHTML = `
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Скопировано!
          `;
          this.classList.add('copied');

          setTimeout(() => {
            this.innerHTML = originalHTML;
            this.classList.remove('copied');
          }, 2000);

          closeVideoPromptModal();
        });
      });

      // Edit/delete (admin)
      if (IS_STAFF) {
        modalContainer.addEventListener('click', async (ev) => {
          const editBtn = ev.target.closest('.js-vcp-edit');
          const delBtn = ev.target.closest('.js-vcp-del');
          const item = ev.target.closest('.prompt-item-modal');
          if (!item) return;

          if (delBtn) {
            ev.preventDefault();
            if (!confirm('Удалить промпт?')) return;
            try {
              await postJSON(`/generate/api/video/prompts/${item.dataset.id}/delete/`, {});
              location.reload();
            } catch (e) { alert(e.message || String(e)); }
            return;
          }
          if (editBtn) {
            ev.preventDefault();
            const title = prompt('Заголовок', item.querySelector('p')?.textContent?.slice(0, 150) || '');
            if (title === null) return;
            const text = prompt('Текст промпта', item.dataset.prompt || '');
            if (text === null) return;
            const en = prompt('Английский промпт', item.dataset.promptEn || '');
            if (en === null) return;
            const order = prompt('Порядок', item.dataset.order || '0');
            if (order === null) return;
            const active = confirm('Сделать активным?');
            try {
              await postJSON(`/generate/api/video/prompts/${item.dataset.id}/update/`, {
                title, prompt_text: text, prompt_en: en, order, is_active: active ? '1' : '0'
              });
              location.reload();
            } catch (e) { alert(e.message || String(e)); }
          }
        });
      }
    } catch (error) {
      modalContainer.innerHTML = '<div class="text-center text-red-500 py-8">Ошибка загрузки промптов</div>';
    }
  }

  function closeVideoPromptModal() {
    const modal = document.getElementById('videoPromptCategoryModal');
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  document.getElementById('closeVideoPromptModal')?.addEventListener('click', closeVideoPromptModal);
  document.getElementById('videoPromptCategoryModal')?.addEventListener('click', function(e) {
    if (e.target.id === 'videoPromptCategoryModal') closeVideoPromptModal();
  });

  function openEditModal(card) {
    const modal = document.getElementById('vpcEditModal');
    if (!modal) return;

    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    document.getElementById('vpcEditId').value = card.dataset.categoryId;
    document.getElementById('vpcEditName').value = card.dataset.name || '';
    document.getElementById('vpcEditDesc').value = card.dataset.desc || '';
    document.getElementById('vpcEditOrder').value = card.dataset.order || '0';
    document.getElementById('vpcEditActive').checked = (card.dataset.active === '1');
  }

  function closeEditModal() {
    const modal = document.getElementById('vpcEditModal');
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  document.getElementById('vpcEditClose')?.addEventListener('click', closeEditModal);
  document.getElementById('vpcEditCancel')?.addEventListener('click', closeEditModal);
  document.getElementById('vpcEditModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'vpcEditModal') closeEditModal();
  });

  document.getElementById('vpcEditSave')?.addEventListener('click', async () => {
    const id = document.getElementById('vpcEditId').value;
    const name = document.getElementById('vpcEditName').value;
    const desc = document.getElementById('vpcEditDesc').value;
    const order = document.getElementById('vpcEditOrder').value;
    const active = document.getElementById('vpcEditActive').checked ? '1' : '0';
    const img = document.getElementById('vpcEditImage').files?.[0];
    const fd = new FormData();
    if (name) fd.append('name', name);
    fd.append('description', desc || '');
    fd.append('order', order || '0');
    fd.append('is_active', active);
    if (img) fd.append('image', img);
    try {
      await postFD(`/generate/api/video/categories/${id}/update/`, fd);
      location.reload();
    }
    catch (e) { alert(e.message || String(e)); }
  });

  // Form submit fallback (progressive enhancement) for video categories
  window.__vpcSubmit = async function(ev) {
    try {
      ev.preventDefault();
      const form = ev.currentTarget || document.getElementById('vpcForm');
      const btn = document.getElementById('vpcCreateBtn');
      const status = document.getElementById('vpcStatus');
      const fd = new FormData(form);
      const name = (fd.get('name') || '').toString().trim();
      if (!name) { alert('Введите название'); return false; }
      if (btn) { btn.disabled = true; btn.textContent = 'Создание...'; }
      if (status) { status.textContent = 'Отправка запроса...'; status.style.color = 'var(--muted)'; }
      const res = await postFD(form.action, fd);
      if (status) { status.textContent = 'Готово: ' + ((res && res.category && res.category.name) || name); status.style.color = '#10b981'; }
      const selMode = (fd.get('mode') || '').toString() || getCurrentVideoMode();
      currentMode = selMode;
      syncAdminModeSelect();
      await loadVideoCategories(selMode);
      try { document.getElementById('videoCategoriesContainer')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch(_) {}
      return false;
    } catch (e) {
      const btn = document.getElementById('vpcCreateBtn');
      const status = document.getElementById('vpcStatus');
      if (status) { status.textContent = 'Ошибка: ' + (e.message || String(e)); status.style.color = '#ef4444'; }
      // Duplicate name → показать/подсветить существующую карточку
      try {
        const fd = new FormData(ev.currentTarget || document.getElementById('vpcForm'));
        const name = (fd.get('name') || '').toString();
        const selMode = (fd.get('mode') || '').toString() || getCurrentVideoMode();
        const msg = (e && e.message ? e.message : String(e)).toLowerCase();
        if (msg.includes('already exists') && name) {
          currentMode = selMode;
          await loadVideoCategories(selMode);
          expandAllVideoCategories();
          highlightVideoCategoryByName(name);
        }
      } catch(_) {}
      alert(e.message || String(e));
      if (btn) { btn.disabled = false; btn.textContent = '+ Категория'; }
      return false;
    }
  };

  // Admin: create category
  if (IS_STAFF) {
    document.getElementById('vpcCreateBtn')?.addEventListener('click', async (ev) => {
      const btn = ev.currentTarget;
      const status = document.getElementById('vpcStatus');
      const name = (document.getElementById('vpcName')?.value || '').trim();
      const desc = (document.getElementById('vpcDesc')?.value || '').trim();
      const order = document.getElementById('vpcOrder')?.value || '0';
      const mode = document.getElementById('vpcMode')?.value || 't2v';
      const active = document.getElementById('vpcActive')?.checked ? '1' : '0';
      const imgInput = document.getElementById('vpcImage');
      if (!name) { alert('Введите название'); return; }
      const fd = new FormData();
      fd.append('name', name);
      if (desc) fd.append('description', desc);
      fd.append('order', order);
      fd.append('mode', mode);
      fd.append('is_active', active);
      if (imgInput?.files?.[0]) fd.append('image', imgInput.files[0]);
      try {
        const old = btn.textContent;
        btn.textContent = 'Создание...';
        btn.disabled = true;
        if (status) { status.textContent = 'Отправка запроса...'; status.style.color = 'var(--muted)'; }
        const res = await postFD('/generate/api/video/categories/create/', fd);
        const created = (res && res.category) ? res.category : null;
        if (status) { status.textContent = 'Готово: ' + ((created && created.name) || name); status.style.color = '#10b981'; }
        // Обновляем список без перезагрузки и гарантируем соответствие режиму
        currentMode = mode;
        syncAdminModeSelect();
        await loadVideoCategories(mode);
        try { document.getElementById('videoCategoriesContainer')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch(_) {}
      } catch (e) {
        if (status) { status.textContent = 'Ошибка: ' + (e.message || String(e)); status.style.color = '#ef4444'; }
        // If duplicate name — перерисовываем список и подсвечиваем уже существующую карточку
        const msg = (e && e.message ? e.message : String(e)).toLowerCase();
        if (msg.includes('already exists')) {
          try {
            await loadVideoCategories(mode);
            expandAllVideoCategories();
            highlightVideoCategoryByName(name);
          } catch(_) {}
        }
        alert(e.message || String(e));
      } finally {
        btn.disabled = false;
        btn.textContent = '+ Категория';
      }
    });
  }

  // Mode change handler
  function handleVideoModeChange() {
    const newMode = getCurrentVideoMode();
    if (newMode !== currentMode) {
      currentMode = newMode;
      syncAdminModeSelect();
      loadVideoCategories(currentMode);
      loadVideoShowcase(currentMode);
    } else {
      // Still sync select to be safe
      syncAdminModeSelect();
    }
  }

  // Listen for mode changes
  document.addEventListener('click', function(e) {
    const tab = e.target.closest('.video-source-tab');
    if (tab) {
      try { localStorage.setItem('gen.videoSource', tab.dataset.source || getCurrentVideoMode() || 't2v'); } catch(_) {}
      setTimeout(handleVideoModeChange, 100);
    }
  });

  document.addEventListener('videoModeChanged', function(e) {
    const mode = e.detail?.mode || getCurrentVideoMode();
    currentMode = mode;
    syncAdminModeSelect();
    loadVideoCategories(mode);
    loadVideoShowcase(mode);
  });

  // Listen for force load event
  document.addEventListener('forceLoadVideoContent', function(e) {
    const mode = e.detail?.mode || getCurrentVideoMode();
    currentMode = mode;
    loadVideoCategories(mode);
    loadVideoShowcase(mode);
  });

  // Initial load when video mode is active
  const videoModeTab = document.querySelector('[data-mode="video"]');
  if (videoModeTab) {
    videoModeTab.addEventListener('click', function() {
      setTimeout(function() {
        currentMode = getCurrentVideoMode();
        loadVideoCategories(currentMode);
        loadVideoShowcase(currentMode);
      }, 300);
    });
  }

  // Load on DOMContentLoaded if video form is visible
  document.addEventListener('DOMContentLoaded', function() {
    const videoContainer = document.getElementById('video-form-container');
    const isVideoVisible = videoContainer && getComputedStyle(videoContainer).display !== 'none';
    if (isVideoVisible) {
      currentMode = getCurrentVideoMode();
      try { localStorage.setItem('gen.videoSource', currentMode || 't2v'); } catch(_) {}
      syncAdminModeSelect();
      loadVideoCategories(currentMode);
      loadVideoShowcase(currentMode);
    }
  });

  // Immediate check - if already loaded and video visible, load content
  (function immediateInit() {
    if (document.readyState === 'loading') return; // Wait for DOMContentLoaded
    const videoContainer = document.getElementById('video-form-container');
    const container = document.getElementById('videoCategoriesContainer');
    const isVideoVisible = videoContainer && getComputedStyle(videoContainer).display !== 'none';
    const needsLoad = container && container.innerHTML.includes('Загрузка');
    if (isVideoVisible && needsLoad) {
      currentMode = getCurrentVideoMode();
      syncAdminModeSelect();
      loadVideoCategories(currentMode);
      loadVideoShowcase(currentMode);
    }
  })();

  // Force load when switching to video tab
  document.addEventListener('click', function(e) {
    const videoTab = e.target.closest('[data-mode="video"]');
    if (videoTab) {
      setTimeout(function() {
        const container = document.getElementById('videoCategoriesContainer');
        if (container && container.innerHTML.includes('Загрузка')) {
          currentMode = getCurrentVideoMode();
          syncAdminModeSelect();
          loadVideoCategories(currentMode);
          loadVideoShowcase(currentMode);
        }
      }, 500);
    }
  });

  // Fallback: Check every 2 seconds if categories are still loading (max 5 attempts)
  let fallbackAttempts = 0;
  const fallbackInterval = setInterval(function() {
    fallbackAttempts++;
    if (fallbackAttempts > 5) {
      clearInterval(fallbackInterval);
      return;
    }
    const videoContainer = document.getElementById('video-form-container');
    const container = document.getElementById('videoCategoriesContainer');
    const isVideoVisible = videoContainer && getComputedStyle(videoContainer).display !== 'none';
    const needsLoad = container && container.innerHTML.includes('Загрузка') && container.dataset.loading !== 'true';
    if (isVideoVisible && needsLoad) {
      currentMode = getCurrentVideoMode();
      syncAdminModeSelect();
      loadVideoCategories(currentMode);
      loadVideoShowcase(currentMode);
      clearInterval(fallbackInterval);
    } else if (categoriesLoaded || (container && !container.innerHTML.includes('Загрузка'))) {
      clearInterval(fallbackInterval);
    }
  }, 2000);
})();
