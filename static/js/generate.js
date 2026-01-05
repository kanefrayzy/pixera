// Clean, stable script for /generate/new
// Removed corrupted legacy blocks (loader, resumePendingImage, broken submit flow).
// This file now only handles:
// - Suggestions system (UI only)
// - Category cards navigation
// - Image model card selection + cost update + Face Retouch UI toggles
// - Showcase helpers (protection overlay)
// Generation queues are handled in image-generation.js and video-generation.js

(function () {
  /* === SUGGESTIONS SYSTEM ================================================ */
  const target = document.getElementById('sgTarget') || document.querySelector('.js-suggest-target');
  const wraps = Array.from(document.querySelectorAll('.js-suggest-wrap'));
  const byCat = new Map(wraps.map(w => [w.dataset.cat, w]));
  wraps.forEach(w => { w.style.display = 'none'; });

  function renderCat(cat) {
    const wrap = byCat.get(cat) || byCat.get('all');
    if (!wrap || !target) return;
    target.innerHTML = '';
    target.className = 'tags';
    const seen = new Set();
    wrap.querySelectorAll('.sg-item').forEach(item => {
      const id = item.getAttribute('data-sid') || item.textContent.trim();
      if (seen.has(id)) return;
      seen.add(id);
      target.appendChild(item.cloneNode(true));
    });
  }
  renderCat('all');

  // Category switching
  document.querySelectorAll('.js-cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active state from all category cards
      document.querySelectorAll('.cat-card').forEach(card => {
        card.classList.remove('active');
        card.setAttribute('aria-selected', 'false');
      });

      // Add active state to clicked card
      const card = btn.closest ? btn.closest('.cat-card') : btn;
      if (card && card.classList.contains('cat-card')) {
        card.classList.add('active');
        card.setAttribute('aria-selected', 'true');
      }

      renderCat(btn.dataset.cat || 'all');
    });
  });

  /* === CATEGORY CARDS NAVIGATION ========================================== */
  const catContainer = document.querySelector('.js-cat-container');
  const leftArrow = document.querySelector('.js-cat-scroll-left');
  const rightArrow = document.querySelector('.js-cat-scroll-right');
  const indicatorsContainer = document.querySelector('.js-cat-indicators');

  if (catContainer && leftArrow && rightArrow) {
    let currentScrollIndex = 0;
    const scrollStep = 200; // pixels to scroll per click

    function updateArrowVisibility() {
      const { scrollLeft, scrollWidth, clientWidth } = catContainer;

      if (scrollLeft <= 0) {
        leftArrow.style.opacity = '0';
        leftArrow.style.pointerEvents = 'none';
      } else {
        leftArrow.style.opacity = '1';
        leftArrow.style.pointerEvents = 'auto';
      }

      if (scrollLeft >= scrollWidth - clientWidth - 1) {
        rightArrow.style.opacity = '0';
        rightArrow.style.pointerEvents = 'none';
      } else {
        rightArrow.style.opacity = '1';
        rightArrow.style.pointerEvents = 'auto';
      }
    }

    function updateScrollIndicators() {
      if (!indicatorsContainer) return;

      const { scrollWidth, clientWidth } = catContainer;
      const needsIndicators = scrollWidth > clientWidth;

      if (!needsIndicators) {
        indicatorsContainer.style.display = 'none';
        return;
      }

      indicatorsContainer.style.display = 'flex';
      const maxScroll = scrollWidth - clientWidth;
      const sections = Math.ceil(maxScroll / scrollStep) + 1;

      indicatorsContainer.innerHTML = '';
      for (let i = 0; i < sections; i++) {
        const indicator = document.createElement('div');
        indicator.className = 'cat-scroll-indicator';
        if (i === currentScrollIndex) indicator.classList.add('active');

        indicator.addEventListener('click', () => {
          const targetScroll = Math.min(i * scrollStep, maxScroll);
          catContainer.scrollTo({ left: targetScroll, behavior: 'smooth' });
          currentScrollIndex = i;
          updateScrollIndicators();
        });

        indicatorsContainer.appendChild(indicator);
      }
    }

    leftArrow.addEventListener('click', () => {
      const newScrollLeft = Math.max(0, catContainer.scrollLeft - scrollStep);
      catContainer.scrollTo({ left: newScrollLeft, behavior: 'smooth' });
      currentScrollIndex = Math.max(0, currentScrollIndex - 1);
      updateScrollIndicators();
    });

    rightArrow.addEventListener('click', () => {
      const maxScroll = catContainer.scrollWidth - catContainer.clientWidth;
      const newScrollLeft = Math.min(maxScroll, catContainer.scrollLeft + scrollStep);
      catContainer.scrollTo({ left: newScrollLeft, behavior: 'smooth' });
      currentScrollIndex = Math.min(Math.ceil(maxScroll / scrollStep), currentScrollIndex + 1);
      updateScrollIndicators();
    });

    catContainer.addEventListener('scroll', () => {
      updateArrowVisibility();

      // Update current scroll index based on scroll position
      const scrollRatio = catContainer.scrollLeft / (catContainer.scrollWidth - catContainer.clientWidth);
      const maxIndex = Math.ceil((catContainer.scrollWidth - catContainer.clientWidth) / scrollStep);
      currentScrollIndex = Math.round(scrollRatio * maxIndex);
      updateScrollIndicators();
    });

    // Initialize visibility and indicators
    setTimeout(() => {
      updateArrowVisibility();
      updateScrollIndicators();
    }, 100);

    // Update on window resize
    window.addEventListener('resize', () => {
      setTimeout(() => {
        updateArrowVisibility();
        updateScrollIndicators();
      }, 100);
    });
  }

  // Insert suggestion text
  const txt = document.getElementById('prompt') || document.querySelector('textarea[name="prompt"]');
  if (target) {
    target.addEventListener('click', (e) => {
      const b = e.target.closest('.js-suggest');
      if (!b || !txt) return;
      const t = (b.dataset.text || b.textContent || '').trim();
      if (!t) return;
      txt.value = txt.value ? txt.value.trim().replace(/[\,\s]*$/, '') + ', ' + t : t;
      txt.focus();
    });
  }

  /* === IMAGE MODEL CARDS (selection + Face Retouch UI) ==================== */
  (function () {
    const container = document.getElementById('image-model-cards');
    const hidden = document.getElementById('image-model-id');
    const costDisplay = document.getElementById('current-model-cost');
    if (!container || !hidden) return;

    const rootEl = document.getElementById('gen-root') || document.body;
    const baseCost = parseInt((rootEl && rootEl.dataset && rootEl.dataset.rawCost) ? rootEl.dataset.rawCost : '10', 10);

    // Model costs mapping (keep in sync with backend special cases)
    const modelCosts = {
      'runware:101@1': baseCost, // Standard
      'bytedance:5@0': 15,       // Seedream
      'bfl:2@2': 15,             // FLUX.1.1 [pro] Ultra
      'runware:108@22': baseCost // Face Retouch (photo->photo)
    };

    const cards = Array.from(container.querySelectorAll('.image-model-card'));

    function select(card) {
      // Clear previous selection styles
      cards.forEach(c => {
        c.dataset.selected = '0';
        c.classList.remove('border-primary', 'is-selected');
        c.classList.add('border-[var(--bord)]');
        c.setAttribute('aria-pressed', 'false');
        c.setAttribute('aria-selected', 'false');
        // Hide selected dot
        const dot = c.querySelector('[data-role="selected-dot"]');
        if (dot) dot.classList.add('hidden');
      });

      if (card) {
        const model = card.dataset.model || '';
        hidden.value = model;
        card.dataset.selected = '1';
        card.classList.add('border-primary', 'is-selected');
        card.classList.remove('border-[var(--bord)]');
        card.setAttribute('aria-pressed', 'true');
        card.setAttribute('aria-selected', 'true');
        // Show selected dot
        const dot = card.querySelector('[data-role="selected-dot"]');
        if (dot) dot.classList.remove('hidden');

        // Update cost display via price calculator
        try {
          const config = card.dataset.config ? JSON.parse(card.dataset.config) : null;
          const cost = config && config.token_cost ? config.token_cost : (modelCosts[model] || baseCost);

          // Use price calculator if available
          if (window.imageGenPriceCalculator) {
            window.imageGenPriceCalculator.setBaseCost(cost);
          } else if (window.updateImageBaseCost) {
            window.updateImageBaseCost(cost);
          } else {
            // Fallback: update directly
            if (costDisplay) costDisplay.textContent = cost;
          }

          const root = document.getElementById('gen-root') || document.body;
          if (root && root.dataset) root.dataset.rawCost = String(cost);
          localStorage.setItem('gen.image.model', model);
        } catch (_) { }

        // Toggle Face Retouch UI
        try {
          const wrap = document.getElementById('retouch-upload');
          const adv = document.getElementById('retouch-advanced');
          const input = document.getElementById('retouchFile');
          if (wrap) {
            if (model === 'runware:108@22') {
              wrap.style.display = 'block';
              if (adv) adv.style.display = 'block';
              if (typeof setupRetouchUI === 'function') setupRetouchUI();
            } else {
              wrap.style.display = 'none';
              if (adv) adv.style.display = 'none';
              if (input) input.value = '';
              const prev = document.getElementById('retouch-preview');
              if (prev) prev.classList.add('hidden');
            }
          }
        } catch (_) { }

        // Update fields via ImageFieldManager
        try {
          if (card.dataset.config) {
            const config = JSON.parse(card.dataset.config);
            if (window.imageFieldManager) {
              window.imageFieldManager.updateFieldsForModel(config);
            } else if (typeof ImageFieldManager !== 'undefined') {
              window.imageFieldManager = new ImageFieldManager();
              window.imageFieldManager.updateFieldsForModel(config);
            }
          }
        } catch (e) {
          console.error('Error updating image fields:', e);
        }
      }
    }

    // Initial selection: prefer saved model, then pre-marked, then first
    (function initSelection() {
      let pre = null;
      try {
        const saved = localStorage.getItem('gen.image.model');
        if (saved) pre = cards.find(c => (c.dataset.model || '') === saved) || null;
      } catch (_) { }
      if (!pre) pre = cards.find(c => c.dataset.selected === '1') || cards[0];
      if (pre) select(pre);
    })();

    cards.forEach(c => {
      c.addEventListener('click', () => select(c));
      c.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          select(c);
        }
      });
    });
  })();

  // Initialize Face Retouch drag-and-drop upload once (shared with image-generation.js)
  function setupRetouchUI() {
    try {
      const area = document.getElementById('retouch-upload-area');
      const input = document.getElementById('retouchFile');
      const preview = document.getElementById('retouch-preview');
      const img = document.getElementById('retouchPreviewImg');
      const removeBtn = document.getElementById('removeRetouchImage');
      const cfg = document.getElementById('retouchCfg');
      const cfgVal = document.getElementById('retouchCfgVal');
      if (!area || !input) return;
      if (area.dataset.bound === '1') return; // bind once
      area.dataset.bound = '1';

      function applyFile(file) {
        if (!file || !/^image\//i.test(file.type)) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
          if (img) img.src = ev.target.result;
          if (preview) preview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
      }

      area.addEventListener('click', () => input.click());
      area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('border-primary'); });
      area.addEventListener('dragleave', () => area.classList.remove('border-primary'));
      area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('border-primary');
        const files = (e.dataTransfer && e.dataTransfer.files) ? e.dataTransfer.files : null;
        const f = files && files[0];
        if (f) {
          try { input.files = files; } catch (_) {}
          applyFile(f);
        }
      });
      input.addEventListener('change', () => applyFile(input.files && input.files[0]));
      if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
          e.preventDefault();
          try { input.value = ''; } catch (_) {}
          if (preview) preview.classList.add('hidden');
          if (img) img.src = '';
        });
      }
      if (cfg && cfgVal) {
        const upd = () => { cfgVal.textContent = String(cfg.value); };
        cfg.addEventListener('input', upd);
        upd();
      }

      const sizeSel = document.getElementById('retouchSize');
      const customWrap = document.getElementById('retouchCustomWrap');
      const wIn = document.getElementById('retouchWidth');
      const hIn = document.getElementById('retouchHeight');
      if (sizeSel && customWrap) {
        const toggle = () => {
          customWrap.classList.toggle('hidden', sizeSel.value !== 'custom');
        };
        sizeSel.addEventListener('change', toggle);
        toggle();
      }

      function clampInt(v, lo, hi) {
        v = parseInt(v || '0', 10);
        if (Number.isNaN(v)) v = 0;
        return Math.max(lo, Math.min(hi, v));
      }
      if (wIn) wIn.addEventListener('change', () => { wIn.value = String(clampInt(wIn.value, 64, 2048)); });
      if (hIn) hIn.addEventListener('change', () => { hIn.value = String(clampInt(hIn.value, 64, 2048)); });
    } catch (_) {}
  }
  // Expose globally for image-models toggle calls
  window.setupRetouchUI = setupRetouchUI;
})();

/* === SHOWCASE IMAGE PROTECTION =========================================== */
(function () {
  // Handle image clicks with confirmation overlay
  document.addEventListener('click', function (e) {
    const imageContainer = e.target.closest('.showcase-image-container');
    const openBtn = e.target.closest('.showcase-open-btn');
    const cancelBtn = e.target.closest('.showcase-cancel-btn');
    const overlay = e.target.closest('.showcase-overlay');

    // If clicked on image or container (but not on overlay)
    if (imageContainer && !overlay) {
      e.preventDefault();
      e.stopPropagation();

      // Close any other open overlays
      document.querySelectorAll('.showcase-overlay.show').forEach(otherOverlay => {
        if (otherOverlay !== imageContainer.querySelector('.showcase-overlay')) {
          otherOverlay.classList.remove('show');
          otherOverlay.closest('.showcase-image-container').classList.remove('clicked');
        }
      });

      // Toggle current overlay
      const currentOverlay = imageContainer.querySelector('.showcase-overlay');
      if (currentOverlay) {
        currentOverlay.classList.add('show');
        imageContainer.classList.add('clicked');
      }
    }

    // If clicked on open button
    if (openBtn) {
      e.preventDefault();
      e.stopPropagation();

      const container = openBtn.closest('.showcase-image-container');
      const imageUrl = container?.dataset.imageUrl;

      if (imageUrl) {
        window.open(imageUrl, '_blank', 'noopener');
      }

      const ov = container?.querySelector('.showcase-overlay');
      if (ov) {
        ov.classList.remove('show');
        container.classList.remove('clicked');
      }
    }

    // If clicked on cancel button
    if (cancelBtn) {
      e.preventDefault();
      e.stopPropagation();

      const container = cancelBtn.closest('.showcase-image-container');
      const ov = container?.querySelector('.showcase-overlay');

      if (ov) {
        ov.classList.remove('show');
        container.classList.remove('clicked');
      }
    }

    // If clicked outside any image container, close all overlays
    if (!imageContainer) {
      document.querySelectorAll('.showcase-overlay.show').forEach(o => {
        o.classList.remove('show');
        o.closest('.showcase-image-container').classList.remove('clicked');
      });
    }
  });

  // Close overlay on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.showcase-overlay.show').forEach(o => {
        o.classList.remove('show');
        o.closest('.showcase-image-container').classList.remove('clicked');
      });
    }
  });

  // Prevent context menu on images to avoid confusion
  document.addEventListener('contextmenu', function (e) {
    if (e.target.closest('.showcase-image')) {
      e.preventDefault();
    }
  });
})();
