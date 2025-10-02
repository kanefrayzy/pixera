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
