/**
 * Image Generation Queue (parity with video queue)
 * - Renders a queue card under image model cards
 * - Multiple results (fan-out) for Face Retouch "Варианты"
 * - Tiles: progress ring + bar, remove tile ✕, Open, Download, Gallery
 * - Clear queue button
 * - Dark/Light theme friendly, Tailwind classes, responsive to 320px
 */
(function() {
  const root = document.getElementById('gen-root') || document.body;
  if (!root) return;
  const USER_KEY = (root.dataset && root.dataset.userKey) ? root.dataset.userKey : 'anon';
  try { console.log('[image-gen] loaded v1, userKey=', USER_KEY, 'ts=', Date.now()); } catch(_) {}
  // Gate heavy work to IMAGE mode only to avoid mixing and UI hangs
  const isImageMode =
    !document.documentElement.classList.contains('mode-video') &&
    (new URLSearchParams(window.location.search).get('type') !== 'video') &&
    (function(){ try { return (localStorage.getItem('gen.topMode') || 'image') !== 'video'; } catch(_) { return true; } })();

  // Clean up old localStorage keys without user isolation
  function cleanupOldKeys() {
    try {
      const oldKeys = ['gen.image.queue', 'gen.image.clearedJobs'];
      oldKeys.forEach(key => {
        if (localStorage.getItem(key)) {
          localStorage.removeItem(key);
        }
      });

      // Also clean up keys from other users
      const allKeys = Object.keys(localStorage);
      allKeys.forEach(key => {
        if (key.startsWith('gen.image.queue::') && !key.endsWith(`::${USER_KEY}`)) {
          localStorage.removeItem(key);
        }
        if (key.startsWith('gen.image.clearedJobs::') && !key.endsWith(`::${USER_KEY}`)) {
          localStorage.removeItem(key);
        }
      });
    } catch(_) {}
  }

  // Run cleanup on load
  cleanupOldKeys();

  const form = document.getElementById('image-generation-form');
  const genBtn = document.getElementById('genBtn');
  const modelHidden = document.getElementById('image-model-id');
  const API_SUBMIT_URL = root.dataset.apiSubmitUrl;
  const API_STATUS_TPL = root.dataset.apiStatusTpl;
  const TOPUP_URL = root.dataset.topupUrl;
  const IS_STAFF = (root.dataset.isStaff || 'false') === 'true';
  const isAuth = (root.dataset.isAuth || 'false') === 'true';
  // Image auto-translate flag (persisted, default ON)
  let imgAutoTranslate = (function() {
    try {
      const v = localStorage.getItem('gen.image.autoTranslate');
      if (v === null || v === undefined) return true;
      return v === '1' || v === 'true';
    } catch(_) { return true; }
  })();

  if (!form || !genBtn || !modelHidden || !API_SUBMIT_URL || !API_STATUS_TPL) return;
  // Initialize image auto-translate toggle UI
  initImgAutoTranslateToggle();

  // Balance check (same logic as generate.js)
  function currentCost() {
    const rc = parseInt(root.dataset.rawCost || '10', 10);
    return IS_STAFF ? 0 : (isFinite(rc) ? rc : 10);
  }
  function canAfford() {
    if (IS_STAFF) return true;
    const cost = currentCost();
    if (cost <= 0) return true;
    try {
      const bal = isAuth
        ? parseInt((document.getElementById('balance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0
        : parseInt((document.getElementById('guestBalance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0;
      return Math.floor(bal / cost) > 0;
    } catch(_) { return true; }
  }

  // CSRF
  function getCSRF() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const v = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
    if (v) return v;
    const cookie = document.cookie.split('; ').find(r => r.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  // Auto-translate toggle UI for images (parity with video)
  function saveImgAutoTranslate(on){
    try { localStorage.setItem('gen.image.autoTranslate', on ? '1' : '0'); } catch(_) {}
  }
  function applyImgATUI(btn, on){
    try {
      btn.classList.toggle('bg-[var(--bord)]', !on);
      btn.classList.toggle('bg-primary/90', on);
      btn.classList.toggle('ring-primary/40', on);
      const dot = btn.querySelector('.dot');
      if (dot) {
        dot.style.transform = on ? 'translateX(20px)' : 'translateX(0px)';
        dot.classList.add('bg-white');
      }
    } catch(_) {}
  }
  function initImgAutoTranslateToggle(){
    const btn = document.getElementById('img-auto-translate-toggle');
    if (!btn) return;
    // initial
    btn.setAttribute('aria-pressed', imgAutoTranslate ? 'true' : 'false');
    applyImgATUI(btn, imgAutoTranslate);
    // events
    btn.addEventListener('click', () => {
      const on = btn.getAttribute('aria-pressed') !== 'true';
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      imgAutoTranslate = !!on;
      saveImgAutoTranslate(imgAutoTranslate);
      applyImgATUI(btn, imgAutoTranslate);
    });
  }

  // LocalStorage helpers
  function loadQueue() {
    try { const raw = localStorage.getItem(`gen.image.queue::${USER_KEY}`); const arr = raw ? JSON.parse(raw) : []; return Array.isArray(arr) ? arr : []; } catch(_) { return []; }
  }
  function saveQueue(arr) {
    try { localStorage.setItem(`gen.image.queue::${USER_KEY}`, JSON.stringify((arr || []).slice(-24))); } catch(_) {}
  }
  function loadClearedJobs() {
    try { const raw = localStorage.getItem(`gen.image.clearedJobs::${USER_KEY}`); const arr = raw ? JSON.parse(raw) : []; return new Set(Array.isArray(arr) ? arr.map(String) : []); } catch(_) { return new Set(); }
  }
  function saveClearedJobs(set) {
    try { localStorage.setItem(`gen.image.clearedJobs::${USER_KEY}`, JSON.stringify(Array.from(set || []))); } catch(_) {}
  }

  let queue = loadQueue();              // [{job_id, status, image_url, createdAt, gallery_id}]
  let clearedJobs = loadClearedJobs();  // Set of job ids
  function loadClearedAt() {
    try { return parseInt(localStorage.getItem(`gen.image.clearedAt::${USER_KEY}`) || '0', 10) || 0; } catch(_) { return 0; }
  }
  function saveClearedAt(ts) {
    try { localStorage.setItem(`gen.image.clearedAt::${USER_KEY}`, String(ts || 0)); } catch(_) {}
  }
  let clearedAt = loadClearedAt();

  // Persisted jobs (button clicked) per user/session
  function loadPersistedJobs() {
    try {
      const raw = localStorage.getItem(`gen.image.persisted::${USER_KEY}`);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr.map(String) : []);
    } catch(_) { return new Set(); }
  }
  function savePersistedJobs(set) {
    try {
      localStorage.setItem(`gen.image.persisted::${USER_KEY}`, JSON.stringify(Array.from(set || [])));
    } catch(_) {}
  }
  let persistedJobs = loadPersistedJobs();
  // Simple lock to avoid duplicate queue submissions on rapid clicks
  let isGenerating = false;

  // Cache result assets in Cache Storage (best-effort; opaque responses are ok)
  function cacheAsset(url){
    try{
      if (url && 'caches' in window) {
        caches.open('gen-assets-v1').then(c => c.add(url)).catch(()=>{});
      }
    }catch(_){}
  }

  // Lazy-load image only when near viewport to avoid heavy initial network
  function lazyLoadImage(imgEl, url){
    try{
      if (!imgEl || !url) return;
      if ('IntersectionObserver' in window){
        const io = new IntersectionObserver((entries) => {
          entries.forEach(en => {
            if (en.isIntersecting) {
              try {
                imgEl.src = url;
                imgEl.loading = 'lazy';
                imgEl.decoding = 'async';
              } catch(_) {}
              io.unobserve(imgEl);
            }
          });
        }, { rootMargin: '200px' });
        io.observe(imgEl);
      } else {
        imgEl.src = url;
      }
    } catch(_) {}
  }

  // Inject responsive CSS for action buttons on small screens (380px -> 320px)
  function ensureResponsiveStyles() {
    if (document.getElementById('img-queue-responsive')) return;
    const s = document.createElement('style');
    s.id = 'img-queue-responsive';
    s.textContent = `
@media (max-width: 420px){
  .img-tile-actions { gap: 6px; }
  .img-tile-actions .img-action { padding: 4px 6px; font-size: 10px; }
}
@media (max-width: 380px){
  .img-tile-actions { flex-wrap: wrap; gap: 4px; max-width: calc(100% - 8px); }
  .img-tile-actions .img-action { padding: 3px 6px; font-size: 9px; }
}
@media (max-width: 350px){
  .img-tile-actions { flex-direction: column; align-items: flex-end; gap: 4px; }
  .img-tile-actions .img-action { padding: 3px 5px; font-size: 9px; }
}
@media (max-width: 330px){
  .img-tile-actions .img-action { padding: 2px 5px; font-size: 8px; }
}
    `.trim();
    try { document.head.appendChild(s); } catch(_) {}
  }

  // "Show more" button for deferred appending of extra results
  function insertShowMoreButton(grid){
    try{
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
        try{
          const list = grid._moreJobs || [];
          const frag = document.createDocumentFragment();
          const batch = list.splice(0, 12);
          batch.forEach(job => {
            const tile = createPendingTile();
            if (job && job.image_url) {
              renderTileResult(tile, job.image_url, job.job_id, job.gallery_id);
              frag.appendChild(tile);
            }
          });
          grid.appendChild(frag);
          if (!list.length) { btn.remove(); grid._hasShowMore = false; }
        } catch(_) {}
      });
    } catch(_) {}
  }

  // TTL: purge items older than 24h and clean up DOM tiles/card (strict)
  // Any items without createdAt are treated as expired to guarantee full cleanup.
  function purgeExpiredQueue() {
    try {
      const TTL_MS = 24 * 60 * 60 * 1000;
      const now = Date.now();
      const removed = new Set();

      // Keep items with createdAt within TTL; collect removed job_ids
      const next = (queue || []).filter(e => {
        const ok = e && e.createdAt && (now - e.createdAt) < TTL_MS;
        if (!ok && e && e.job_id) removed.add(String(e.job_id));
        // Legacy items without createdAt are removed as expired for strict 24h TTL
        return ok;
      });

      if (next.length !== (queue || []).length) {
        queue = next;
        saveQueue(queue);

        // Mark expired jobs as cleared so they never re-appear from bootstrap
        if (removed.size) {
          try {
            removed.forEach(id => {
              clearedJobs.add(String(id));
            });
            saveClearedJobs(clearedJobs);
          } catch (_) {}
        }

        // Remove corresponding tiles from DOM and hide the card if empty
        const grid = document.getElementById('image-results-grid');
        if (grid) {
          if (removed.size) {
            grid.querySelectorAll('.image-result-tile').forEach(tile => {
              const jid = tile && tile.dataset ? tile.dataset.jobId : null;
              if (jid && removed.has(String(jid))) {
                try { tile.remove(); } catch(_) {}
              }
            });
          }
          // If no tiles left, remove the whole card until next generation
          if (!grid.querySelector('.image-result-tile')) {
            const card = document.getElementById('image-queue-card');
            if (card) { try { card.remove(); } catch(_) {} }
          }
        }
      }
    } catch (_) {}
  }

  // UI host
  function ensureQueueUI() {
    ensureResponsiveStyles();
    purgeExpiredQueue();
    if (document.getElementById('image-queue-card')) return;
    const placeholder = document.getElementById('image-queue-placeholder');
    const host = placeholder || document.getElementById('gen-root') || document.body;
    const card = document.createElement('div');
    card.id = 'image-queue-card';
    card.className = 'card p-6';
    card.innerHTML = `
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-lg sm:text-xl font-bold">Очередь генерации</h3>
        <button type="button" id="clear-image-queue-btn" class="px-3 py-1.5 rounded-lg border border-[var(--bord)] bg-[var(--bg-card)] text-xs sm:text-sm">
          Очистить очередь
        </button>
      </div>
      <div class="mt-2 rounded-xl border border-[var(--bord)] bg-[var(--bg-card)] p-3 text-xs text-[var(--muted)]">
        Результаты (фото) хранятся локально 24 часа. По истечении срока очередь очищается автоматически. Данные не покидают ваш браузер.
      </div>
      <div id="image-results-grid" class="mt-4 grid gap-3"></div>
    `;
    if (placeholder) {
      placeholder.appendChild(card);
    } else {
      host.appendChild(card);
    }
    try { console.log('[image-gen] queue UI created'); } catch(_) {}
    // Оптимизация производительности и фиксированный размер карточек
    if (!document.getElementById('image-queue-perf-style')) {
      const st = document.createElement('style');
      st.id = 'image-queue-perf-style';
      st.textContent = `
        /* Фиксированный размер карточек для всех устройств */
        #image-results-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 0.75rem;
          contain: layout style;
        }

        /* Телефоны: 2 карточки */
        @media (max-width: 640px) {
          #image-results-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
          }
        }

        /* ПК: автоматическое заполнение */
        @media (min-width: 641px) {
          #image-results-grid {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          }
        }

        /* Оптимизация производительности */
        .image-result-tile {
          content-visibility: auto;
          contain-intrinsic-size: 200px 250px;
          will-change: auto;
        }

        .image-result-tile img {
          transform: translateZ(0);
          backface-visibility: hidden;
        }

        /* Кнопка сохранить */
        .img-save-btn {
          position: absolute;
          bottom: 0.5rem;
          right: 0.5rem;
          z-index: 30;
          height: 2rem;
          padding: 0 0.75rem;
          border-radius: 1rem;
          background: rgba(99, 102, 241, 0.9);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.375rem;
          border: none;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          white-space: nowrap;
          font-size: 0.75rem;
          font-weight: 500;
        }

        /* Кнопки */
        .image-tile-remove:hover,
        .img-save-btn:hover {
          transform: scale(1.05);
        }

        .image-tile-remove:active,
        .img-save-btn:active {
          transform: scale(0.95);
        }

        /* Мобильные стили */
        @media (max-width: 640px) {
          .image-tile-remove {
            width: 2rem !important;
            height: 2rem !important;
          }
          .image-tile-remove svg {
            width: 1rem !important;
            height: 1rem !important;
          }
          .img-save-btn {
            height: 1.75rem !important;
            padding: 0 0.525rem !important;
            font-size: 0.6875rem !important;
            gap: 0.25rem !important;
            bottom: 0.375rem !important;
            right: 1.175rem !important;
          }
          .img-save-btn svg {
            width: 0.75rem !important;
            height: 0.75rem !important;
          }
        }

        /* Очень маленькие экраны */
        @media (max-width: 375px) {
          .img-save-btn {
            height: 2rem !important;
            padding: 0 0.5rem !important;
            font-size: 0.625rem !important;
          }
        }
      `;
      try { document.head.appendChild(st); } catch(_) {}
    }

    card.querySelector('#clear-image-queue-btn')?.addEventListener('click', async () => {
      try { console.log('[image-gen] clear clicked; queue size=', (queue||[]).length); } catch(_) {}
      // backend: permanently clear server-side queue for this owner
      try {
        await fetch('/generate/api/queue/clear', { method: 'POST', headers: { 'X-CSRFToken': getCSRF() }, credentials: 'same-origin' }).catch(()=>{});
      } catch(_) {}
      // mark ALL jobs (pending and done) as cleared to suppress re-appearance/restores
      queue.forEach(e => { if (e.job_id) clearedJobs.add(String(e.job_id)); });
      saveClearedJobs(clearedJobs);
      // remember clear moment and persist it to suppress completed bootstrap restore
      clearedAt = Date.now();
      saveClearedAt(clearedAt);
      // wipe DOM
      card.querySelectorAll('.image-result-tile').forEach(el => { try { el.remove(); } catch(_) {} });
      // clear state
      queue = [];
      saveQueue(queue);
      // hide card until new generation
      try { card.remove(); } catch(_) {}
    });

    // Delegated actions on tiles (persist/remove)
    card.addEventListener('click', (e) => {
      // Persist to "Мои генерации"
      const pbtn = e.target.closest('.img-save-btn');
      if (pbtn) {
        const tile = pbtn.closest('.image-result-tile');
        const jid = tile && tile.dataset ? tile.dataset.jobId : null;
        if (jid) { persistJob(String(jid), pbtn); }
        return;
      }

      // Remove tile from queue UI
      const btn = e.target.closest('.tile-remove-btn');
      if (!btn) return;
      const tile = btn.closest('.image-result-tile');
      if (!tile) return;
      const jid = tile.dataset.jobId;
      if (jid) {
        // backend: permanently remove this job
        try {
          fetch('/generate/api/queue/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCSRF() },
            credentials: 'same-origin',
            body: 'job_id=' + encodeURIComponent(String(jid))
          }).catch(()=>{});
        } catch(_) {}
        clearedJobs.add(String(jid));
        saveClearedJobs(clearedJobs);
      }
      try { tile.remove(); } catch(_) {}
    });

    // Restore previous queue
    restoreQueueInto(card.querySelector('#image-results-grid'));
  }

  function restoreQueueInto(grid) {
    if (!grid) return;
    const items = [...queue].sort((a,b)=> (b.createdAt||0)-(a.createdAt||0));
    items.forEach(item => {
      if (clearedJobs.has(String(item.job_id))) return;
      // Skip legacy mixed-in video entries (no image_url but has video_url)
      if (item && !item.image_url && item.video_url) {
        try { clearedJobs.add(String(item.job_id)); saveClearedJobs(clearedJobs); } catch(_) {}
        return;
      }
      const tile = createPendingTile();
      grid.appendChild(tile);
      if (item.status === 'done' && item.image_url) {
        renderTileResult(tile, item.image_url, item.job_id, item.gallery_id);
      } else if (item.status === 'failed') {
        renderTileError(tile, item.error || 'Ошибка генерации');
      } else {
        setTileProgress(tile, 10, 'Возобновляем…');
        pollStatusInline(item.job_id, tile);
      }
    });
  }

  function addOrUpdateEntry(jobId, patch) {
    if (!jobId) return;
    const id = String(jobId);
    const idx = queue.findIndex(e => String(e.job_id) === id);
    if (idx >= 0) queue[idx] = { ...queue[idx], ...patch, job_id: id };
    else queue.push({ job_id: id, createdAt: Date.now(), ...patch });
    saveQueue(queue);
  }

  // Persist job in "Мои генерации"
  async function persistJob(jobId, btn) {
    if (!jobId) return;
    try {
      if (btn) {
        btn.disabled = true;
        // Add spinning animation while processing
        btn.innerHTML = `
          <svg style="width: 0.875rem; height: 0.875rem; flex-shrink: 0; animation: spin 1s linear infinite;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10" opacity="0.25"/>
            <path opacity="0.75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <span class="save-btn-text">Добавляем...</span>
        `;
        btn.setAttribute('aria-label', 'Добавляем…');
      }
      const r = await fetch(`/generate/api/job/${jobId}/persist`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF(), 'X-Requested-With': 'fetch' },
        credentials: 'same-origin'
      });
      const j = await r.json().catch(()=>({}));
      if (!r.ok || j.ok === false) throw new Error(j.error || ('HTTP ' + r.status));
      // mark persisted in local storage
      try {
        persistedJobs.add(String(jobId));
        savePersistedJobs(persistedJobs);
      } catch(_) {}

      // Без автоскачивания — по требованию: добавляем в «Мои генерации» без загрузки файла

      if (btn) {
        // Show success checkmark with text
        btn.innerHTML = `
          <svg style="width: 0.875rem; height: 0.875rem; flex-shrink: 0;" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
          <span class="save-btn-text">Сохранен</span>
        `;
        btn.disabled = true;
        btn.style.opacity = '0.7';
        btn.style.pointerEvents = 'none';
        btn.style.animation = 'pulse 0.6s ease-in-out';
        btn.setAttribute('aria-label', isAuth ? 'Сохранено в профиле' : 'Сохранен в галерею');
        // brief success pulse
        try { setTimeout(()=> { if(btn.style) btn.style.animation = ''; }, 600); } catch(_) {}
      }
    } catch (e) {
      if (btn) {
        btn.disabled = false;
        // Restore original icon and text on error
        btn.innerHTML = `
          <svg style="width: 0.875rem; height: 0.875rem; flex-shrink: 0;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
          <span class="save-btn-text">Добавить</span>
        `;
        btn.setAttribute('aria-label', isAuth ? 'Сохранить в профиле' : 'Добавить в галерею');
      }
      // soft alert; do not break UI
      try { console.warn('Persist failed', e); } catch(_) {}
    }
  }

  // Tiles
  function createPendingTile() {
    const tile = document.createElement('div');
    tile.className = 'image-result-tile rounded-xl border border-[var(--bord)] bg-[var(--bg-card)] overflow-hidden shadow-sm animate-fade-in-scale';
    tile.setAttribute('data-status','pending');
    tile.innerHTML = `
      <div class="relative aspect-square group bg-gradient-to-br from-[var(--bg-card)] to-[var(--bg-2)] overflow-hidden rounded-xl">
        <!-- Кнопка удаления -->
        <button type="button" class="image-tile-remove" aria-label="Удалить">
          <svg style="width: 0.875rem; height: 0.875rem;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>

        <!-- Premium Puzzle Loader -->
        <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4 z-10">
          <!-- Puzzle Grid Container -->
          <div class="puzzle-grid relative w-24 h-24 sm:w-28 sm:h-28">
            <!-- Puzzle pieces (3x3 grid) -->
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

          <!-- Status Text -->
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

    // Inject puzzle animation styles if not already present
    if (!document.getElementById('puzzle-loader-styles')) {
      const style = document.createElement('style');
      style.id = 'puzzle-loader-styles';
      style.textContent = `
        /* Puzzle Grid Layout */
        .puzzle-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          grid-template-rows: repeat(3, 1fr);
          gap: 2px;
        }

        /* Individual Puzzle Piece */
        .puzzle-piece {
          background: linear-gradient(135deg, var(--primary) 0%, #8b5cf6 100%);
          border-radius: 2px;
          opacity: 0;
          transform: scale(0) rotate(0deg);
          animation: puzzlePop 1.2s ease-in-out infinite;
          animation-delay: var(--delay);
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
        }

        /* Light theme adjustments */
        html[data-theme="light"] .puzzle-piece {
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
        }

        /* Puzzle Pop Animation */
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

        /* Spin animation */
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Pulse animation */
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        /* Shimmer Effect */
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }

        .animate-shimmer {
          animation: shimmer 2s infinite;
        }

        /* Spin animation */
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Pulse animation */
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        /* Fade in scale animation */
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .animate-fade-in-scale {
          animation: fadeInScale 0.3s ease-out;
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
          .puzzle-grid {
            width: 80px !important;
            height: 80px !important;
            gap: 1.5px;
          }
        }

        @media (max-width: 375px) {
          .puzzle-grid {
            width: 72px !important;
            height: 72px !important;
            gap: 1px;
          }
        }

        @media (max-width: 320px) {
          .puzzle-grid {
            width: 64px !important;
            height: 64px !important;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Обработчик удаления для pending tile
    try {
      const removeBtn = tile.querySelector('.image-tile-remove');
      if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();

          // Анимация удаления
          tile.style.transition = 'all 0.3s ease';
          tile.style.transform = 'scale(0.8)';
          tile.style.opacity = '0';

          setTimeout(() => {
            try {
              tile.remove();

              // Проверяем, остались ли карточки
              const grid = document.getElementById('image-results-grid');
              if (grid && !grid.querySelector('.image-result-tile')) {
                const card = document.getElementById('image-queue-card');
                if (card) card.remove();
              }
            } catch(_) {}
          }, 300);
        });
      }
    } catch(_) {}

    return tile;
  }

  function setTileProgress(tile, pct, text) {
    try {
      // Throttle progress DOM updates to keep UI snappy
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      const lastTs = tile._pt || 0;
      const lastPct = tile._pp || 0;
      const diffPct = Math.abs((pct || 0) - (lastPct || 0));
      if (!text && now - lastTs < 120 && diffPct < 3) return; // skip tiny changes
      tile._pt = now;
      tile._pp = pct;

      const statusEl = tile.querySelector('[data-role="tile-status"]');
      const txtEl = tile.querySelector('[data-role="tile-phase"]');

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

      // Animate puzzle pieces based on progress (batch DOM writes)
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
    } catch(_) {}
  }

  function renderTileResult(tile, imageUrl, jobId, galleryId) {
    try { tile.setAttribute('data-status','done'); } catch(_) {}
    if (jobId) try { tile.dataset.jobId = String(jobId); } catch(_) {}
    if (jobId && imageUrl) addOrUpdateEntry(jobId, { status:'done', image_url: imageUrl, gallery_id: galleryId, completedAt: Date.now() });

    // Обновляем баланс в реальном времени после успешной генерации
    try {
      if (window.balanceUpdater && typeof window.balanceUpdater.fetch === 'function') {
        window.balanceUpdater.fetch();
      }
    } catch(e) {
      console.log('[image-gen] Balance update skipped:', e.message);
    }

    tile.innerHTML = `
      <div class="relative aspect-square bg-black overflow-hidden rounded-xl">
        <img data-src="${imageUrl}" alt="Результат" loading="lazy" decoding="async" fetchpriority="low" class="absolute inset-0 w-full h-full object-cover"/>

        <!-- Кнопка удаления (верхний левый угол) -->
        <button type="button" class="image-tile-remove" aria-label="Удалить" style="position: absolute; top: 0.5rem; left: 0.5rem; z-index: 30; width: 2rem; height: 2rem; border-radius: 9999px; background: rgba(220, 38, 38, 0.9); color: white; display: flex; align-items: center; justify-content: center; border: none; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
          <svg style="width: 0.875rem; height: 0.875rem;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>

        <!-- Кнопка открыть (верхний правый угол) -->
        <a href="${imageUrl}" target="_blank" class="image-open-btn" aria-label="Открыть" style="position: absolute; top: 0.5rem; right: 0.5rem; z-index: 30; width: 2rem; height: 2rem; border-radius: 9999px; background: rgba(0,0,0,0.7); color: white; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
          <svg style="width: 0.875rem; height: 0.875rem;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </a>

        <!-- Кнопка сохранить (нижний правый угол) -->
        <button type="button"
                class="img-save-btn"
                aria-label="${isAuth ? 'Сохранить в профиле' : 'Добавить в галерею'}">
          <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
          <span class="save-btn-text">Добавить</span>
        </button>
      </div>
    `;
    try {
      const imgEl = tile.querySelector('img');
      if (imgEl) {
        lazyLoadImage(imgEl, imageUrl);
        imgEl.addEventListener('load', () => {
          try { imgEl.decode && imgEl.decode().catch(()=>{}); } catch(_) {}
        }, { once: true });
      }
    } catch(_) {}

    // Best-effort cache
    try { cacheAsset(imageUrl); } catch(_){}

    // If already persisted earlier, lock the button state on render
    try {
      const pbtn = tile.querySelector('.img-save-btn');
      if (pbtn && jobId && persistedJobs && persistedJobs.has(String(jobId))) {
        // Change icon to checkmark with text for persisted state
        pbtn.innerHTML = `
          <svg style="width: 0.875rem; height: 0.875rem; flex-shrink: 0;" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
          <span class="save-btn-text">Сохранен</span>
        `;
        pbtn.disabled = true;
        pbtn.classList.add('opacity-70','pointer-events-none');
        pbtn.setAttribute('aria-label', isAuth ? 'Сохранено в профиле' : 'Сохранен в галерею');
      }
    } catch(_) {}

    // Обработчик удаления карточки
    try {
      const removeBtn = tile.querySelector('.image-tile-remove');
      if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();

          // Удаляем из очереди
          if (jobId) {
            try {
              const id = String(jobId);
              queue = queue.filter(e => String(e.job_id) !== id);
              saveQueue(queue);
            } catch(_) {}
          }

          // Анимация удаления
          tile.style.transition = 'all 0.3s ease';
          tile.style.transform = 'scale(0.8)';
          tile.style.opacity = '0';

          setTimeout(() => {
            try {
              tile.remove();

              // Проверяем, остались ли карточки
              const grid = document.getElementById('image-results-grid');
              if (grid && !grid.querySelector('.image-result-tile')) {
                const card = document.getElementById('image-queue-card');
                if (card) card.remove();
              }
            } catch(_) {}
          }, 300);
        });
      }
    } catch(_) {}
  }

  function renderTileError(tile, message) {
    try { tile.setAttribute('data-status','failed'); } catch(_) {}
    tile.innerHTML = `
      <div class="relative aspect-square bg-[var(--bg-card)] flex items-center justify-center">
        <div class="text-center p-4">
          <div class="text-red-500 font-semibold mb-1">Ошибка</div>
          <div class="text-xs sm:text-sm text-[var(--muted)]">${escapeHtml((message || 'Не удалось сгенерировать изображение') + ' Токены не списаны.')}</div>
        </div>
      </div>
    `;
  }

  function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

  // Polling
  async function pollStatusInline(jobId, tile, attempts = 0) {
    const maxAttempts = 120;
    const delayBase = document.hidden ? 2000 : 1000;
    if (jobId) addOrUpdateEntry(jobId, { status: 'pending' });

    if (attempts >= maxAttempts) {
      if (tile) setTileProgress(tile, 98, 'Почти готово…');
      setTimeout(()=>pollStatusInline(jobId, tile, attempts+1), 2000);
      return;
    }

    try {
      const url = API_STATUS_TPL.replace('12345', String(jobId));
      const r = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      if (r.status === 404 || r.status === 403) {
        // Foreign/forbidden job: drop from this user's UI and suppress re-appearance
        try { clearedJobs.add(String(jobId)); saveClearedJobs(clearedJobs); } catch(_) {}
        try { addOrUpdateEntry(jobId, { status: 'forbidden' }); } catch(_) {}
        try { tile && tile.remove(); } catch(_) {}
        return;
      }
      const j = await r.json().catch(()=> ({}));

      if (j.failed) {
        if (tile) renderTileError(tile, j.error || 'Ошибка генерации');
        addOrUpdateEntry(jobId, { status:'failed', error: j.error || '' });
        return;
      }

      if (j.done && j.image && j.image.url) {
        // Suppress if cleared
        const idx = queue.findIndex(e => String(e.job_id) === String(jobId));
        const createdAt = (idx>=0 && queue[idx].createdAt) || 0;
        if ((clearedAt && createdAt && createdAt <= clearedAt) || clearedJobs.has(String(jobId))) {
          addOrUpdateEntry(jobId, { status:'done', image_url: j.image.url, completedAt: Date.now(), gallery_id: j.gallery_id });
          try { tile && tile.remove(); } catch(_) {}
          return;
        }
        if (!tile || !tile.isConnected) {
          ensureQueueUI();
          const grid = document.getElementById('image-results-grid');
          if (grid) {
            const nt = createPendingTile();
            grid.prepend(nt);
            tile = nt;
          }
        }
        renderTileResult(tile, j.image.url, jobId, j.gallery_id);
      } else {
        const p = (j && typeof j.progress === 'number')
          ? Math.min(98, j.progress)
          : Math.min(98, (attempts / maxAttempts) * 100);
        if (tile) setTileProgress(tile, p, 'Генерация изображения…');
        setTimeout(()=>pollStatusInline(jobId, tile, attempts+1), delayBase);
      }
    } catch (e) {
      setTimeout(()=>pollStatusInline(jobId, tile, attempts+1), 1000);
    }
  }

  // Restore completed jobs from server (only show finished results)
  async function bootstrapCompletedJobs() {
    try {
      const r = await fetch('/generate/api/completed-jobs?type=image', { headers: { 'X-Requested-With': 'fetch' } });
      let j = await r.json().catch(()=>null);
      try { console.log('[image-gen] bootstrapCompletedJobs total=', (j && j.jobs && j.jobs.length) || 0); } catch(_) {}
      if (!j || !j.success || !j.jobs || !j.jobs.length) return;

      ensureQueueUI();
      const grid = document.getElementById('image-results-grid');
      if (!grid) return;

      // Show only completed jobs for current user (batched to minimize reflows)
      const frag = document.createDocumentFragment();
      const LIMIT = 12;
      let shown = 0;
      grid._moreJobs = grid._moreJobs || [];
      j.jobs.forEach(job => {
        const jid = String(job.job_id);
        if (clearedJobs.has(jid) || queue.some(e => String(e.job_id) === jid)) return;
        const createdAtTs = job.created_at ? Date.parse(job.created_at) : 0;
        if ((clearedAt && createdAtTs && createdAtTs <= clearedAt) || (job.generation_type === 'video')) return;

        if (job.status === 'done' && (job.image_url || job.video_url)) {
          if (shown < LIMIT) {
            const tile = createPendingTile();
            // Only render image items in the image queue; video queue handles videos
            if (job.generation_type !== 'video' && job.image_url) {
              renderTileResult(tile, job.image_url, jid, job.gallery_id);
            } else {
              try { tile.remove(); } catch(_) {}
              return;
            }

            frag.appendChild(tile);
            shown++;
          } else {
            // Queue for later "Show more"
            grid._moreJobs.push({
              job_id: jid,
              image_url: job.image_url,
              gallery_id: job.gallery_id,
              status: 'done'
            });
          }

          addOrUpdateEntry(jid, {
            status: 'done',
            image_url: job.image_url || job.video_url,
            gallery_id: job.gallery_id,
            completedAt: Date.now()
          });
        }
      });
      const appendFrag = () => {
        try { grid.appendChild(frag); } catch(_) {}
        // Add "Show more" trigger if there are more jobs
        if (grid._moreJobs && grid._moreJobs.length && !document.getElementById(grid.id + '-show-more')) {
          insertShowMoreButton(grid);
        }
      };
      if ('requestIdleCallback' in window) {
        requestIdleCallback(appendFrag);
      } else {
        setTimeout(appendFrag, 0);
      }
    } catch(_) {}
  }

  // Submit one image request
  async function submitOne(prompt, selectedModel, variantIndex, totalVariants) {
    const fd = new FormData();
    fd.append('prompt', prompt);
    // pass client flag for server-side toggleable translation
    try { fd.append('auto_translate', imgAutoTranslate ? '1' : '0'); } catch(_) {}
    if (selectedModel) fd.append('model_id', selectedModel);

    // Add reference images if any
    try {
      // Try both compact and full component classes
      const refSection = document.querySelector('.reference-upload-compact[data-target="image"]') ||
                        document.querySelector('.reference-upload-section[data-target="image"]');
      if (refSection) {
        // Wait for component initialization if needed
        if (typeof refSection.getReferenceFiles === 'function') {
          const refFiles = refSection.getReferenceFiles();
          if (refFiles && refFiles.length > 0) {
            console.log('[image-gen] Attaching', refFiles.length, 'reference images');
            refFiles.forEach((file, idx) => {
              fd.append('reference_images', file);
              console.log('[image-gen] Added reference image:', file.name, file.size, 'bytes');
            });
          } else {
            console.log('[image-gen] No reference files to attach');
          }
        } else {
          console.warn('[image-gen] Reference component not initialized yet');
        }
      } else {
        console.log('[image-gen] No reference upload section found (tried .reference-upload-compact and .reference-upload-section)');
      }
    } catch(e) {
      console.error('[image-gen] Failed to attach reference images:', e);
    }

    // Face Retouch (photo -> photo) special fields
    if (selectedModel === 'runware:108@22') {
      const f = document.getElementById('retouchFile')?.files?.[0];
      if (f) fd.append('reference_image', f);

      const cfg = document.getElementById('retouchCfg');
      const sched = document.getElementById('retouchScheduler');
      const accel = document.getElementById('retouchAcceleration');
      if (cfg) fd.append('cfg_scale', String(cfg.value || '4'));
      if (sched && sched.value) fd.append('scheduler', sched.value);
      if (accel && accel.value) fd.append('acceleration', accel.value);

      const ratio = document.getElementById('retouchSize')?.value || '';
      if (ratio) fd.append('retouch_ratio', ratio);
      if (ratio === 'custom') {
        const w = document.getElementById('retouchWidth')?.value;
        const h = document.getElementById('retouchHeight')?.value;
        if (w) fd.append('retouch_width', String(w));
        if (h) fd.append('retouch_height', String(h));
      }

      // Always 1 per request for fan-out consistency
      fd.append('number_results', '1');

      // Optional: introduce slight variation via "seed" by variant index (if backend supports)
      // fd.append('seed', String(Date.now() + variantIndex));
    } else {
      // Regular models: add number_results from totalVariants
      if (totalVariants > 1) {
        fd.append('number_results', String(totalVariants));
      }
    }

    const resp = await fetch(API_SUBMIT_URL, {
      method: 'POST',
      body: fd,
      headers: { 'X-CSRFToken': getCSRF(), 'X-Requested-With': 'fetch' },
      credentials: 'same-origin'
    });
    const j = await resp.json().catch(()=> ({}));
    if (!resp.ok) throw new Error(j.error || ('HTTP ' + resp.status));
    return j;
  }

  async function generateMulti() {
    const promptEl = document.getElementById('prompt');
    const prompt = (promptEl?.value || '').trim();
    if (!prompt) { try { promptEl?.focus(); } catch(_) {} return; }

    const selectedModel = (modelHidden.value || '').trim();
    if (!selectedModel) return;

    // Guard against double starts
    if (isGenerating) return;
    isGenerating = true;

    // Compute variants - read from number_results field
    let count = 1;
    if (selectedModel === 'runware:108@22') {
      // Face Retouch uses retouchVariants
      const vr = parseInt(document.getElementById('retouchVariants')?.value || '1', 10);
      count = isFinite(vr) && vr > 0 ? Math.min(4, vr) : 1;
    } else {
      // Regular models use number_results
      const numberResultsEl = document.getElementById('number-results');
      if (numberResultsEl) {
        const nr = parseInt(numberResultsEl.value || '1', 10);
        count = isFinite(nr) && nr > 0 ? Math.max(1, Math.min(20, nr)) : 1;
      }
    }

    // Check balance with total cost (base cost × quantity)
    if (!IS_STAFF) {
      const baseCost = currentCost();
      const totalCost = baseCost * count;
      try {
        const bal = isAuth
          ? parseInt((document.getElementById('balance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0
          : parseInt((document.getElementById('guestBalance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0;
        if (bal < totalCost) {
          isGenerating = false;
          window.location.href = TOPUP_URL;
          return;
        }
      } catch(_) {}
    }

    ensureQueueUI();
    const grid = document.getElementById('image-results-grid');

    // Create tiles for each expected result
    const tiles = [];
    for (let i = 0; i < count; i++) {
      const tile = createPendingTile();
      if (grid) grid.prepend(tile);
      tiles.push(tile);
    }

    try {
      // Submit ONE request with number_results parameter
      const j = await submitOne(prompt, selectedModel, 0, count);

      // Handle possible redirect-only responses (fallback): extract job id from URL if present
      if (!j?.image?.url && !j?.image_url && !j?.id && !j?.job_id && j?.redirect) {
        try {
          const rx = /(\d{3,})\/?$/; // last numeric segment
          const m = String(j.redirect).match(rx);
          if (m && m[1]) {
            const jid2 = m[1];
            // Update first tile with job status
            if (tiles[0]) {
              setTileProgress(tiles[0], 5, 'Генерация изображений…');
              addOrUpdateEntry(jid2, { status: 'pending' });
              pollStatusInline(jid2, tiles[0]);
            }
            // Remove extra tiles since we only have one job
            tiles.slice(1).forEach(t => { try { t.remove(); } catch(_) {} });
            isGenerating = false;
            return;
          }
        } catch(_) {}
      }

      const doneUrl = j?.image?.url || j?.image_url || '';
      const jid = String(j?.id || j?.job_id || '').trim();

      if (doneUrl) {
        // Single result returned immediately
        if (tiles[0]) {
          renderTileResult(tiles[0], doneUrl, jid || '', j?.gallery_id || null);
        }
        // Remove extra tiles
        tiles.slice(1).forEach(t => { try { t.remove(); } catch(_) {} });
      } else if (jid) {
        // Job queued - update first tile and poll
        if (tiles[0]) {
          setTileProgress(tiles[0], 5, `Генерация ${count} изображени${count === 1 ? 'я' : count < 5 ? 'й' : 'й'}…`);
          addOrUpdateEntry(jid, { status: 'pending' });
          pollStatusInline(jid, tiles[0]);
        }
        // Remove extra tiles - backend will generate multiple results for one job
        tiles.slice(1).forEach(t => { try { t.remove(); } catch(_) {} });
      } else {
        // Error - show on first tile
        if (tiles[0]) {
          renderTileError(tiles[0], 'Некорректный ответ сервера');
        }
        tiles.slice(1).forEach(t => { try { t.remove(); } catch(_) {} });
      }
    } catch (e) {
      // Error - show on first tile
      if (tiles[0]) {
        renderTileError(tiles[0], e?.message || 'Ошибка отправки запроса');
      }
      tiles.slice(1).forEach(t => { try { t.remove(); } catch(_) {} });
    }

    // Release generation lock
    isGenerating = false;
  }

  // Prevent default form submit; use button click to start queue flow
  try {
    genBtn.type = 'button';
  } catch(_) {}

  genBtn.addEventListener('click', () => {
    generateMulti().catch(()=>{});
  });

  // Intercept legacy form submit from older script; capture phase to cancel other listeners
  try {
    form.addEventListener('submit', function(e){
      e.preventDefault();
      if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
      generateMulti().catch(()=>{});
    }, true);
  } catch(_) {}

  // On load: restore queue UI with completed jobs only (IMAGE mode only)
  try {
    if (isImageMode) {
      // Pre-render queue UI immediately for instant UX; restore and bootstrap asynchronously
      ensureQueueUI();
      // Load completed jobs from server (only finished results), scheduled after first paint
      if ('requestIdleCallback' in window) {
        requestIdleCallback(() => { try { bootstrapCompletedJobs(); } catch(_) {} });
      } else {
        setTimeout(() => { try { bootstrapCompletedJobs(); } catch(_) {} }, 0);
      }
      // TTL: Авто-очистка просроченных элементов каждые 60 минут
      if (!window._imgTTLTimer) {
        window._imgTTLTimer = setInterval(() => { try { purgeExpiredQueue(); } catch(_) {} }, 60 * 60 * 1000);
      }
    } else {
      // Hide image queue in VIDEO mode to prevent mixing
      const iq = document.getElementById('image-queue-card');
      if (iq) iq.style.display = 'none';
    }
  } catch(_) {}
})();
