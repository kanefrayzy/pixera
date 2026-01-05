/**
 * Image models selection UI (optimized).
 * - Single delegated listeners instead of N listeners on each card
 * - Minimal DOM churn: toggle only previous/next selected
 * - Updates hidden input (#image-model-id), Face Retouch UI and visible cost
 * - Persists last selected model in localStorage
 */
document.addEventListener('DOMContentLoaded', function () {
  try {
    const container = document.getElementById('image-model-cards');
    const hidden = document.getElementById('image-model-id');
    if (!container || !hidden) return;

    const root = document.getElementById('gen-root') || document.body;
    const costEl = document.getElementById('current-model-cost');
    let baseCost = 10;
    try {
      baseCost = parseInt((root && root.dataset && root.dataset.rawCost) ? root.dataset.rawCost : '10', 10);
      if (!isFinite(baseCost)) baseCost = 10;
    } catch (_) { baseCost = 10; }

    const cards = Array.from(container.querySelectorAll('.image-model-card'));
    if (!cards.length) return;

    const SPECIAL_COSTS = new Set(['bytedance:5@0', 'bfl:2@2']);
    let selectedCard = null;

    function updateFaceRetouchUI(on) {
      try {
        const wrap = document.getElementById('retouch-upload');
        const adv = document.getElementById('retouch-advanced');
        const input = document.getElementById('retouchFile');
        if (wrap) {
          wrap.style.display = on ? 'block' : 'none';
          if (adv) adv.style.display = on ? 'block' : 'none';
          if (!on && input) {
            input.value = '';
            const prev = document.getElementById('retouch-preview');
            if (prev) prev.classList.add('hidden');
          }
        }
      } catch (_) {}
    }

    function setModel(model) {
      hidden.value = model;

      // Toggle Face Retouch fields
      const isFace = (model === 'runware:108@22');
      updateFaceRetouchUI(isFace);

      // Update visible and effective cost
      const specialCost = SPECIAL_COSTS.has(model) ? 15 : baseCost;
      try {
        if (costEl) costEl.textContent = String(specialCost);
        if (root && root.dataset) root.dataset.rawCost = String(specialCost);
      } catch (_) {}

      // Persist selection
      try { localStorage.setItem('gen.image.model', model); } catch (_) {}
    }

    function applySelection(card) {
      if (!card || card === selectedCard) return;

      // Unselect previous
      if (selectedCard) {
        selectedCard.dataset.selected = '0';
        selectedCard.classList.remove('border-primary', 'is-selected');
        selectedCard.classList.add('border-[var(--bord)]');
        selectedCard.setAttribute('aria-pressed', 'false');
        selectedCard.setAttribute('aria-selected', 'false');
      }

      // Select new
      selectedCard = card;
      selectedCard.dataset.selected = '1';
      selectedCard.classList.add('border-primary', 'is-selected');
      selectedCard.classList.remove('border-[var(--bord)]');
      selectedCard.setAttribute('aria-pressed', 'true');
      selectedCard.setAttribute('aria-selected', 'true');

      setModel(selectedCard.dataset.model || '');
    }

    // Initial selection: saved -> pre-marked -> first
    let initCard = null;
    try {
      const saved = localStorage.getItem('gen.image.model') || '';
      if (saved) initCard = cards.find(c => (c.dataset.model || '') === saved) || null;
    } catch (_) {}

    if (!initCard) initCard = cards.find(c => c.dataset.selected === '1') || cards[0] || null;
    if (initCard) applySelection(initCard);

    // Delegated interactions (one listener)
    container.addEventListener('click', function (e) {
      const card = e.target && e.target.closest ? e.target.closest('.image-model-card') : null;
      if (!card || !container.contains(card)) return;
      applySelection(card);
    }, { passive: true });

    container.addEventListener('keydown', function (e) {
      const card = e.target && e.target.closest ? e.target.closest('.image-model-card') : null;
      if (!card) return;
      const k = e.key;
      if (k === 'Enter' || k === ' ') {
        e.preventDefault();
        applySelection(card);
      }
    });

    // Horizontal scroller: arrow controls
    const section = document.getElementById('image-model-section');
    if (section) {
      const leftBtn = section.querySelector('.image-model-nav-btn.left');
      const rightBtn = section.querySelector('.image-model-nav-btn.right');

      if (leftBtn && rightBtn) {
        leftBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const gap = 12;
          const cardWidth = Math.round((container.clientWidth - gap * 2) / 3);
          const delta = Math.max(160, cardWidth + gap);
          container.scrollBy({ left: -delta, behavior: 'smooth' });
        }, { passive: false });

        rightBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const gap = 12;
          const cardWidth = Math.round((container.clientWidth - gap * 2) / 3);
          const delta = Math.max(160, cardWidth + gap);
          container.scrollBy({ left: delta, behavior: 'smooth' });
        }, { passive: false });
      }

      // Update arrows disabled state (start/end)
      const updateArrows = () => {
        const atStart = (container.scrollLeft || 0) <= 1;
        const atEnd = (container.scrollLeft + container.clientWidth) >= (container.scrollWidth - 1);
        if (leftBtn) { leftBtn.classList.toggle('disabled', atStart); leftBtn.setAttribute('aria-disabled', atStart ? 'true' : 'false'); }
        if (rightBtn) { rightBtn.classList.toggle('disabled', atEnd); rightBtn.setAttribute('aria-disabled', atEnd ? 'true' : 'false'); }
      };
      updateArrows();
      container.addEventListener('scroll', updateArrows, { passive: true });
      window.addEventListener('resize', updateArrows);
    }

  } catch (_) {}
});
