// Generate page script
(function(){
  /* === SUGGESTIONS SYSTEM ================================================ */
  const target = document.getElementById('sgTarget') || document.querySelector('.js-suggest-target');
  const wraps = Array.from(document.querySelectorAll('.js-suggest-wrap'));
  const byCat = new Map(wraps.map(w => [w.dataset.cat, w]));
  wraps.forEach(w => { w.style.display = 'none'; });

  function renderCat(cat){
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

  /* === SHOWCASE FILTERS =================================================== */
  document.querySelectorAll('.js-sh-cat').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.js-sh-cat').forEach(b => {
        b.classList.remove('bg-primary/15', 'text-primary', 'border-primary/30');
        b.classList.add('bg-black/[.04]', 'dark:bg-white/5');
      });
      btn.classList.add('bg-primary/15', 'text-primary', 'border-primary/30');
      btn.classList.remove('bg-black/[.04]', 'dark:bg-white/5');
      const cat = btn.dataset.cat;
      document.querySelectorAll('article[data-cat]').forEach(card => {
        card.style.display = (cat === 'all' || card.dataset.cat === cat) ? '' : 'none';
      });
    });
  });

  // Insert showcase prompt
  document.querySelectorAll('.js-insert-prompt').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = btn.dataset.prompt || '';
      if (!p || !txt) return;
      txt.value = p;
      txt.focus();
      try { txt.scrollIntoView({behavior:'smooth', block:'center'}); } catch(e) {}
    });
  });

  /* === GENERATION LOGIC =================================================== */
  const root = document.getElementById('gen-root') || document.body;
  const API_SUBMIT_URL = root.dataset.apiSubmitUrl;
  const API_STATUS_TPL = root.dataset.apiStatusTpl;
  const JOB_DETAIL_TPL = root.dataset.jobDetailTpl;
  const TOPUP_URL = root.dataset.topupUrl;

  const IS_STAFF = (root.dataset.isStaff || 'false') === 'true';
  const isAuth = (root.dataset.isAuth || 'false') === 'true';
  const rawCost = parseInt(root.dataset.rawCost || '10', 10);
  const effectiveCost = IS_STAFF ? 0 : rawCost;

  const genBtn = document.getElementById('genBtn');
  const loEl = document.querySelector('[data-auth-left], [data-guest-left]');
  const authLeftAttr = (loEl?.dataset.authLeft) || '0';
  const guestLeftAttr = (loEl?.dataset.guestLeft) || '0';
  let leftTotal = isAuth ? parseInt(authLeftAttr, 10) || 0 : parseInt(guestLeftAttr, 10) || 0;

  if (IS_STAFF) {
    const span = document.getElementById('gensLeft');
    if (span) span.innerHTML = '&infin;';
    if (loEl) loEl.setAttribute('data-auth-left', '999999');
    const topUp = document.getElementById('topUpLink');
    if (topUp) topUp.remove();
    leftTotal = 999999;
  }

  try {
    const bal = isAuth
      ? parseInt((document.getElementById('balance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0
      : parseInt((document.getElementById('guestBalance')?.textContent || '0').replace(/\D+/g, ''), 10) || 0;

    if (effectiveCost > 0) {
      const calcLeft = Math.floor(bal / effectiveCost);
      if (!leftTotal || leftTotal < calcLeft) {
        leftTotal = calcLeft;
        const span = document.getElementById('gensLeft');
        if (span) span.textContent = String(calcLeft);
        if (isAuth) loEl?.setAttribute('data-auth-left', String(calcLeft));
        else loEl?.setAttribute('data-guest-left', String(calcLeft));
      }
    } else {
      const span = document.getElementById('gensLeft');
      if (span) span.innerHTML = '&infin;';
    }
  } catch(e) {}

  if (!IS_STAFF && effectiveCost > 0 && leftTotal <= 0) {
    if (genBtn) {
      genBtn.textContent = 'Пополнить';
      genBtn.type = 'button';
      genBtn.addEventListener('click', () => window.location.href = TOPUP_URL);
    }
  }

  /* === LOADER ============================================================= */
  const glx = document.getElementById('glx');
  const bar = document.getElementById('glxBar');
  const pctEl = document.getElementById('glxPct');
  const phaseEl = document.getElementById('glxPhase');
  let startTs = 0, ready = false, finishCb = null;

  function show() { glx.classList.remove('hidden'); glx.setAttribute('aria-hidden', 'false'); }
  function hide() { glx.classList.add('hidden'); glx.setAttribute('aria-hidden', 'true'); }

  function setProgress(p) {
    p = Math.max(0, Math.min(100, p));
    bar.style.width = p.toFixed(0) + '%';
    pctEl.textContent = p.toFixed(0) + '%';
  }

  function runTimeline(cb) {
    finishCb = cb;
    ready = false;
    startTs = performance.now();
    setProgress(0);
    (function tick() {
      const now = performance.now();
      const elapsed = now - startTs;
      const p = Math.min(100, (1 - Math.pow(1 - Math.min(1, elapsed / 10000), 3)) * 100);
      setProgress(p);
      if (elapsed >= 10000 && ready) { setProgress(100); setTimeout(() => finishCb && finishCb(), 350); return; }
      if (!glx.classList.contains('hidden')) requestAnimationFrame(tick);
    })();
  }
  function signalReady() { ready = true; }
  document.getElementById('glxMin')?.addEventListener('click', hide);

  /* === API CALLS ========================================================== */
  const form = document.querySelector('form');
  async function submitTask(prompt) {
    const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
    const fd = new FormData(); fd.append('prompt', prompt);
    const r = await fetch(API_SUBMIT_URL, { method: 'POST', headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch' }, body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ('Submit failed: ' + r.status));
    return j;
  }
  async function poll(jobId) {
    const url = API_STATUS_TPL.replace('12345', jobId);
    let delay = 900;
    while (true) {
      const r = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      const j = await r.json().catch(() => ({}));
      if (j.failed) throw new Error(j.error || 'Ошибка генерации');
      if (j.done && j.image && j.image.url) { signalReady(); return; }
      await new Promise(rs => setTimeout(rs, delay));
      delay = Math.min(2500, delay * 1.15);
    }
  }

  form?.addEventListener('submit', async (e) => {
    const costNow = parseInt((root.dataset.rawCost || '10'), 10);
    const effCostNow = IS_STAFF ? 0 : costNow;

    if (effCostNow > 0) {
      const leftAttr = isAuth
        ? (document.querySelector('[data-auth-left]')?.dataset.authLeft || '0')
        : (document.querySelector('[data-guest-left]')?.dataset.guestLeft || '0');
      const left = parseInt(leftAttr, 10) || 0;
      if (left <= 0) { e.preventDefault(); window.location.href = TOPUP_URL; return; }
    }

    e.preventDefault();
    const prompt = (txt.value || '').trim();
    if (!prompt) { txt.focus(); return; }

    const btn = document.getElementById('genBtn');
    const prev = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Отправляю…';

    // Показываем лоадер сразу
    show();
    phaseEl.textContent = 'Отправка запроса...';
    setProgress(0);

    try {
      const res = await submitTask(prompt);
      if (res && res.redirect) { window.location.href = res.redirect; return; }
      const id = res.id || res.job_id; if (!id) throw new Error('Некорректный ответ API (нет id)');

      // Обновляем фазу после успешной отправки
      phaseEl.textContent = 'Генерация изображения...';
      runTimeline(() => window.location.href = JOB_DETAIL_TPL.replace('12345', id));
      poll(id).catch(err => { alert(err.message || String(err)); hide(); });
    } catch (err) {
      alert(err.message || String(err)); hide();
    } finally {
      btn.disabled = false; btn.textContent = prev;
    }
  });

  /* === ADMIN FEATURES ===================================================== */
  const SG_URL_CREATE = '/generate/api/suggestions/create/';
  const SG_URL_UPDATE_TPL = '/generate/api/suggestions/12345/update/';
  const SG_URL_DELETE_TPL = '/generate/api/suggestions/12345/delete/';
  const CAT_URL_CREATE = '/generate/api/suggestion-categories/create/';
  const CAT_URL_UPDATE_TPL = '/generate/api/suggestion-categories/123/update/';
  const CAT_URL_DELETE_TPL = '/generate/api/suggestion-categories/123/delete/';

  async function postJSON(url, data) {
    const csrf = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
    const fd = new FormData(); Object.entries(data || {}).forEach(([k, v]) => fd.append(k, v));
    const r = await fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch' }, body: fd });
    let j = {}; try { j = await r.json(); } catch(_) {}
    if (!r.ok || j.ok === false) throw new Error(j.error || ('Ошибка: ' + r.status));
    return j;
  }

  function slugify(text) {
    const map = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'};
    return (text || '').toString().trim().toLowerCase()
      .replace(/[а-яё]/g, ch => map[ch] || '')
      .replace(/[\s_]+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
  }

  if (IS_STAFF) {
    const nameInput = document.getElementById('catName');
    const slugInput = document.getElementById('catSlug');
    const activeCb = document.getElementById('catActive');
    const addBtn = document.getElementById('catAdd');

    if (nameInput && slugInput) {
      nameInput.addEventListener('input', () => {
        if (!slugInput.value.trim()) slugInput.value = slugify(nameInput.value);
      });
    }

    if (addBtn) {
      addBtn.addEventListener('click', async () => {
        const name = (nameInput?.value || '').trim();
        let slug = (slugInput?.value || '').trim();
        const is_active = activeCb?.checked ? '1' : '0';
        if (!name) { alert('Введите название категории'); return; }
        if (!slug) slug = slugify(name);
        try { await postJSON(CAT_URL_CREATE, { name, slug, is_active }); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      });
    }

    const sgAddBtn = document.getElementById('sgAdd');
    if (sgAddBtn) {
      sgAddBtn.addEventListener('click', async () => {
        const cat = (document.getElementById('sgCat') || {}).value || '';
        const title = (document.getElementById('sgTitle') || {}).value?.trim() || '';
        const text = (document.getElementById('sgText') || {}).value?.trim() || '';
        if (!title || !text) { alert('Заполни заголовок и текст'); return; }
        try { await postJSON(SG_URL_CREATE, { category: cat, title, text }); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      });
    }

    document.addEventListener('click', async (e) => {
      const sgEdit = e.target.closest('.js-sg-edit');
      const sgDel = e.target.closest('.js-sg-del');
      const catEdit = e.target.closest('.js-cat-edit');
      const catDel = e.target.closest('.js-cat-del');

      if (sgEdit) {
        e.stopPropagation(); e.preventDefault();
        const id = sgEdit.dataset.id;
        const curTitle = sgEdit.dataset.title || '';
        const curText = sgEdit.dataset.text || '';
        const title = prompt('Заголовок подсказки:', curTitle); if (title === null) return;
        const text = prompt('Текст подсказки:', curText); if (text === null) return;
        try { await postJSON(SG_URL_UPDATE_TPL.replace('12345', id), { title, text }); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      }

      if (sgDel) {
        e.stopPropagation(); e.preventDefault();
        if (!confirm('Удалить эту подсказку?')) return;
        const id = sgDel.dataset.id;
        try { await postJSON(SG_URL_DELETE_TPL.replace('12345', id), {}); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      }

      if (catEdit) {
        e.stopPropagation(); e.preventDefault();
        const id = catEdit.dataset.id;
        const curName = catEdit.dataset.name || '';
        const curSlug = catEdit.dataset.slug || '';
        const name = prompt('Название категории:', curName); if (name === null) return;
        let slug = prompt('Slug категории:', curSlug); if (slug === null) return;
        slug = (slug || '').trim() || slugify(name);
        try { await postJSON(CAT_URL_UPDATE_TPL.replace('123', id), { name, slug }); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      }

      if (catDel) {
        e.stopPropagation(); e.preventDefault();
        if (!confirm('Удалить категорию и связи с подсказками?')) return;
        const id = catDel.dataset.id;
        try { await postJSON(CAT_URL_DELETE_TPL.replace('123', id), {}); location.reload(); }
        catch (e) { alert(e.message || String(e)); }
      }
    });
  }
})();
