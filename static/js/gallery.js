// static/js/gallery.js
(function () {
  // --- utils ---
  function getCookie(name) {
    const value = (`; ${document.cookie}`).split(`; ${name}=`).pop();
    return value ? decodeURIComponent(value.split(';').shift()) : null;
  }

  function animateLike(btn, likedNow) {
    // лёгкая анимация «пульса» сердца и счётчика
    try {
      btn.classList.toggle('is-active', likedNow);
      btn.setAttribute('aria-pressed', likedNow ? 'true' : 'false');

      const heart = btn.querySelector('.heart');
      if (heart) {
        heart.style.transition = 'transform .14s ease';
        heart.style.transform = 'scale(1.25)';
        setTimeout(() => { heart.style.transform = 'scale(1)'; }, 140);
      }
      const cnt = btn.querySelector('[data-like-count]');
      if (cnt) {
        cnt.style.transition = 'transform .14s ease';
        cnt.style.transform = 'translateY(-2px)';
        setTimeout(() => { cnt.style.transform = 'translateY(0)'; }, 140);
      }
    } catch (_) {}
  }

  // --- delegated click handler ---
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-like[data-like-url]');
    if (!btn || btn.classList.contains('disabled')) return;

    e.preventDefault();

    const url = btn.getAttribute('data-like-url');
    if (!url) return;

    const cntNode = btn.querySelector('[data-like-count]');
    const prevCount = cntNode ? parseInt(cntNode.textContent || '0', 10) || 0 : 0;
    const wasActive = btn.classList.contains('is-active');

    // оптимистичное обновление
    const optimisticCount = wasActive ? Math.max(0, prevCount - 1) : prevCount + 1;
    if (cntNode) cntNode.textContent = optimisticCount.toString();
    animateLike(btn, !wasActive);

    fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') || '',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: new URLSearchParams() // пустое тело
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      })
      .then((data) => {
        // приводим к фактическому состоянию с сервера
        if (!data || !data.ok) throw new Error('bad payload');
        if (cntNode && typeof data.count === 'number') {
          cntNode.textContent = String(data.count);
        }
        animateLike(btn, !!data.liked);
      })
      .catch(() => {
        // откатываем оптимизм при ошибке
        if (cntNode) cntNode.textContent = String(prevCount);
        animateLike(btn, wasActive);
      });
  });
})();
