(function(){
  const container = document.getElementById('trending-grid');
  const section = document.getElementById('community');
  if (!container || !section) return;

  const endpoint = section.getAttribute('data-trending-endpoint');
  if (!endpoint) return;

  function setActive(btn){
    document.querySelectorAll('[data-trend-switch]').forEach(b=>{
      const small = b.classList.contains('text-sm');
      b.classList.remove('btn-active', 'btn-primary');
      b.classList.add('btn-ghost');
      b.removeAttribute('data-selected');
      b.setAttribute('aria-selected','false');
      if (small) b.classList.add('text-sm');
    });
    if (btn){
      const small = btn.classList.contains('text-sm');
      btn.classList.add('btn-active');
      btn.classList.remove('btn-ghost');
      btn.classList.add('btn-primary');
      btn.setAttribute('data-selected','true');
      btn.setAttribute('aria-selected','true');
      if (small) btn.classList.add('text-sm');
    }
  }

  function renderSkeleton(){
    const items = 8;
    const cards = Array.from({length: items}).map(()=>
      '<article class="skeleton-card">\
        <div class="skeleton-img"></div>\
        <div class="skeleton-meta"></div>\
      </article>'
    ).join('');
    container.innerHTML = '<div class="skeleton-grid">'+cards+'</div>';
  }

  async function loadMode(by, btn){
    try {
      renderSkeleton();
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set('by', by);
      const r = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!r.ok) throw new Error('HTTP '+r.status);
      const html = await r.text();
      container.innerHTML = html;
      setActive(btn);
    } catch(err){
      console.error('Failed to load trending snippet', err);
    }
  }

  function onClick(e){
    const btn = e.target.closest('[data-trend-switch]');
    if (!btn) return;
    e.preventDefault();
    const by = btn.getAttribute('data-by') || 'likes';
    loadMode(by, btn);
  }

  document.addEventListener('click', onClick, { passive: false });

  // Set default active state
  const initial = document.querySelector('[data-trend-switch][data-by="likes"]');
  if (initial) setActive(initial);
})();

/* Accounts search + recommendations (Instagram-like) */
(function(){
  const wrap = document.getElementById('accFollowSection');
  if (!wrap) return; // show only for authenticated
  const searchInput = document.getElementById('accSearchInput');
  const resBox = document.getElementById('accSearchResults');
  const recsBox = document.getElementById('accRecs');
  const recsRefresh = document.getElementById('accRecsRefresh');

  const searchEndpoint = wrap.getAttribute('data-search-endpoint');
  const recsEndpoint = wrap.getAttribute('data-recs-endpoint');
  const toggleEndpoint = wrap.getAttribute('data-toggle-endpoint');

  const getCSRF = () => (window.AIGallery && window.AIGallery.getCSRFToken && window.AIGallery.getCSRFToken()) || (document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/)||[])[1] || '';

  function avatarHTML(u){
    const sizeBase = 'w-9 h-9';
    const sizeSm = 'sm:w-10 sm:h-10';
    const href = '/dashboard/profile/' + encodeURIComponent(u.username || '');
    if (u.avatar_url) {
      return `<a href="${href}" class="shrink-0" aria-label="@${u.username}">
                <img src="${u.avatar_url}" alt="${u.username}" class="${sizeBase} ${sizeSm} rounded-full object-cover ring-1 ring-[var(--bord)]">
              </a>`;
    }
    const first = (u.name && u.name.trim()[0]) || (u.username && u.username.trim()[0]) || 'U';
    return `<a href="${href}" class="shrink-0" aria-label="@${u.username}">
              <span class="${sizeBase} ${sizeSm} rounded-full bg-gradient-to-br from-primary to-blue-600 grid place-items-center text-white text-xs sm:text-[13px] font-bold">${first.toUpperCase()}</span>
            </a>`;
  }

  function followBtnHTML(u){
    const isFollowing = !!u.is_following;
    const base = `btn ${isFollowing ? 'btn-ghost' : 'btn-primary'}`;
    // Full width on very small screens to avoid overflow; shrink-0 to prevent squish
    return `<button type="button"
              class="${base} text-xs sm:text-sm sm:ml-0 ml-auto w-full sm:w-auto justify-center shrink-0 whitespace-nowrap px-3 py-2 rounded-xl"
              data-follow-btn="1"
              data-username="${u.username}"
              aria-pressed="${isFollowing ? 'true' : 'false'}">
              ${isFollowing ? 'Отписаться' : 'Подписаться'}
            </button>`;
  }

  function cardHTML(u){
    // Responsive, wraps on small screens; tailwind-only styling for spacing/contrast
    const href = '/dashboard/profile/' + encodeURIComponent(u.username || '');
    return `<div class="user-card flex sm:flex-nowrap flex-wrap items-center gap-3 p-3 rounded-2xl border border-[var(--bord)] bg-white/40 dark:bg-white/5">
      ${avatarHTML(u)}
      <a href="${href}" class="min-w-0 flex-1 no-underline hover:text-primary">
        <div class="font-medium text-[var(--text)] truncate max-w-full text-sm sm:text-base">${(u.name || u.username) || ''}</div>
        <div class="text-xs text-[var(--muted)] truncate max-w-full">@${u.username} • ${(u.followers || 0)} подписч.</div>
      </a>
      ${followBtnHTML(u)}
    </div>`;
  }

  function renderUsers(box, list){
    if (!box) return;
    if (!list || !list.length) {
      box.innerHTML = `<div class="text-sm text-[var(--muted)] px-1">Ничего не найдено</div>`;
      return;
    }
    box.innerHTML = list.map(cardHTML).join('');
  }

  async function search(q){
    try {
      const url = new URL(searchEndpoint, window.location.origin);
      if (q) url.searchParams.set('q', q);
      url.searchParams.set('limit', '12');
      const r = await fetch(url.toString(), { headers: { 'X-Requested-With': 'fetch' } });
      const j = await r.json();
      if (j && j.ok) renderUsers(resBox, j.users || []);
    } catch(e){
      console.warn('search failed', e);
    }
  }

  async function loadRecs(){
    try {
      const url = new URL(recsEndpoint, window.location.origin);
      url.searchParams.set('limit', '12');
      const r = await fetch(url.toString(), { headers: { 'X-Requested-With': 'fetch' } });
      const j = await r.json();
      if (j && j.ok) renderUsers(recsBox, j.users || []);
    } catch(e){
      console.warn('recs failed', e);
    }
  }

  function debounce(fn, wait){
    let t;
    return function(...args){
      clearTimeout(t);
      t = setTimeout(()=>fn.apply(this, args), wait);
    };
  }

  // Follow toggle (reuse global FollowUI if exists)
  async function followToggle(username, btn){
    if (window.FollowUI && typeof window.FollowUI.toggle === 'function') {
      await window.FollowUI.toggle(username, btn);
      return;
    }
    try {
      const fd = new FormData();
      fd.append('username', username);
      const r = await fetch(toggleEndpoint, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF(), 'X-Requested-With': 'fetch' },
        body: fd
      });
      const j = await r.json();
      if (j && j.ok) {
        const following = !!j.following;
        if (btn) {
          btn.classList.toggle('btn-primary', !following);
          btn.classList.toggle('btn-ghost', following);
          btn.setAttribute('aria-pressed', String(following));
          btn.textContent = following ? 'Отписаться' : 'Подписаться';
        }
      }
    } catch(e){
      console.error('follow toggle error', e);
    }
  }

  // Events
  if (searchInput) {
    searchInput.addEventListener('input', debounce((e)=>{
      const q = (e.target.value || '').trim();
      if (q.length === 0) {
        resBox && (resBox.innerHTML = '');
        return;
      }
      search(q);
    }, 280));
  }

  if (recsRefresh) {
    recsRefresh.addEventListener('click', (e)=>{
      e.preventDefault();
      loadRecs();
    });
  }

  document.addEventListener('click', async (e)=>{
    const btn = e.target.closest('[data-follow-btn="1"]');
    if (!btn) return;
    e.preventDefault();
    const username = btn.getAttribute('data-username') || '';
    if (!username) return;
    await followToggle(username, btn);
  });

  // Initial load
  loadRecs();
})();
