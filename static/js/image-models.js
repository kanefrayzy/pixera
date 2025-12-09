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
  // Horizontal scroller: 3 in a row with arrow controls (compact cards)
  try {
    // Inject styles once
    if (!document.getElementById('image-models-horizontal-style')) {
      const st = document.createElement('style');
      st.id = 'image-models-horizontal-style';
      st.textContent = `
#image-model-cards{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px;-ms-overflow-style:none;scrollbar-width:none}
#image-model-cards::-webkit-scrollbar{display:none}
.image-model-card-wrap{flex:0 0 calc(33.333% - 8px);scroll-snap-align:start}
/* make cards a bit more compact */
#image-model-cards .card-hero{min-height:150px!important}
.model-nav-btn{position:absolute;top:50%;transform:translateY(-50%);z-index:10;width:34px;height:34px;border-radius:9999px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.55);color:#fff;border:1px solid rgba(255,255,255,.25);box-shadow:0 2px 8px rgba(0,0,0,.25)}
.model-nav-btn.disabled{opacity:.4;pointer-events:none;filter:grayscale(.4)}
html[data-theme="light"] .model-nav-btn{background:rgba(0,0,0,.5);border-color:rgba(0,0,0,.15)}
.model-nav-btn:hover{background:rgba(0,0,0,.75)}
.model-nav-btn.left{left:4px}
.model-nav-btn.right{right:4px}
      `;
      document.head.appendChild(st);
    }
    // Attach arrow buttons near the models row
    const parent = container.parentElement;
    if (parent) {
      if (getComputedStyle(parent).position === 'static') { parent.style.position = 'relative'; }
      if (!parent.querySelector('.model-nav-btn.left')) {
        const mk = (dir) => {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'model-nav-btn ' + (dir<0?'left':'right');
          b.setAttribute('aria-label', dir<0?'Назад':'Вперёд');
          b.innerHTML = dir<0
            ? '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>'
            : '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>';
          b.addEventListener('click', () => {
            try {
              const gap = 12;
              const cardWidth = Math.round((container.clientWidth - gap * 2) / 3);
              const delta = Math.max(160, cardWidth + gap);
              container.scrollBy({ left: dir * delta, behavior: 'smooth' });
            } catch(_) {}
          });
          parent.appendChild(b);
        };
        mk(-1); mk(1);
        // Update arrows disabled state (start/end)
        const updateArrows = () => {
          const leftB = parent.querySelector('.model-nav-btn.left');
          const rightB = parent.querySelector('.model-nav-btn.right');
          const atStart = (container.scrollLeft || 0) <= 1;
          const atEnd = (container.scrollLeft + container.clientWidth) >= (container.scrollWidth - 1);
          if (leftB) { leftB.classList.toggle('disabled', atStart); leftB.setAttribute('aria-disabled', atStart ? 'true' : 'false'); }
          if (rightB) { rightB.classList.toggle('disabled', atEnd); rightB.setAttribute('aria-disabled', atEnd ? 'true' : 'false'); }
        };
        updateArrows();
        container.addEventListener('scroll', updateArrows, { passive: true });
        window.addEventListener('resize', updateArrows);
      }
    }
  } catch (_) {}

  } catch (_) {}
});
