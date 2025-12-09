// Ultra-optimized showcase with lazy loading, virtual scrolling, and WebP support
(function() {
  'use strict';

  const grid = document.getElementById('showcaseGrid');
  if (!grid) return;

  const data = window.showcaseGalleryData || [];
  let currentCategory = 'all';
  let visibleItems = [];
  const ITEMS_PER_PAGE = 12;
  let currentPage = 1;

  // Intersection Observer для ленивой загрузки изображений
  const imgObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        const src = img.dataset.src;
        if (src) {
          img.src = src;
          img.removeAttribute('data-src');
          imgObserver.unobserve(img);
        }
      }
    });
  }, { rootMargin: '50px' });

  // Фильтрация данных
  function filterData(category) {
    return category === 'all'
      ? data
      : data.filter(item => item.category === category);
  }

  // Создание карточки (минимальный HTML)
  function createCard(item) {
    const firstImg = item.images && item.images[0];
    if (!firstImg) return '';

    return `
      <div class="showcase-image-container group" data-image-url="${firstImg.full}">
        <div class="relative aspect-square rounded-xl overflow-hidden bg-[var(--bord)]">
          <img
            data-src="${firstImg.thumb}"
            alt="${item.title || ''}"
            class="showcase-image w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
            loading="lazy"
            decoding="async"
            width="400"
            height="400">
          <div class="showcase-overlay">
            <div class="showcase-overlay-content">
              <button class="showcase-open-btn">Открыть</button>
              <button class="showcase-cancel-btn">Отмена</button>
            </div>
          </div>
        </div>
      </div>`;
  }

  // Рендер страницы
  function renderPage() {
    const filtered = filterData(currentCategory);
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageItems = filtered.slice(start, end);

    const html = pageItems.map(createCard).join('');
    grid.innerHTML = html || '<div class="col-span-full text-center text-[var(--muted)] py-8">Примеры не найдены</div>';

    // Запускаем ленивую загрузку для новых изображений
    requestAnimationFrame(() => {
      grid.querySelectorAll('img[data-src]').forEach(img => imgObserver.observe(img));
    });

    // Показываем кнопку "Показать ещё" если есть ещё элементы
    updateLoadMoreButton(filtered.length, end);
  }

  // Кнопка "Показать ещё"
  function updateLoadMoreButton(total, shown) {
    let btn = document.getElementById('showcaseLoadMore');

    if (shown < total) {
      if (!btn) {
        btn = document.createElement('button');
        btn.id = 'showcaseLoadMore';
        btn.className = 'btn btn-primary mx-auto mt-6';
        btn.textContent = 'Показать ещё';
        btn.onclick = () => {
          currentPage++;
          const filtered = filterData(currentCategory);
          const start = (currentPage - 1) * ITEMS_PER_PAGE;
          const end = start + ITEMS_PER_PAGE;
          const newItems = filtered.slice(start, end);

          const html = newItems.map(createCard).join('');
          grid.insertAdjacentHTML('beforeend', html);

          requestAnimationFrame(() => {
            grid.querySelectorAll('img[data-src]').forEach(img => imgObserver.observe(img));
          });

          updateLoadMoreButton(filtered.length, end);
        };
        grid.parentElement.appendChild(btn);
      }
      btn.style.display = 'inline-flex';
    } else if (btn) {
      btn.style.display = 'none';
    }
  }

  // Обработчик фильтров
  document.querySelectorAll('.js-showcase-filter').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.js-showcase-filter').forEach(b => {
        b.classList.remove('bg-primary/15', 'text-primary', 'border-primary/30');
      });
      this.classList.add('bg-primary/15', 'text-primary', 'border-primary/30');

      currentCategory = this.dataset.category || 'all';
      currentPage = 1;
      renderPage();
    });
  });

  // Обработчик кликов на изображения
  grid.addEventListener('click', function(e) {
    const container = e.target.closest('.showcase-image-container');
    const openBtn = e.target.closest('.showcase-open-btn');
    const cancelBtn = e.target.closest('.showcase-cancel-btn');

    if (openBtn) {
      e.preventDefault();
      e.stopPropagation();
      const url = container?.dataset.imageUrl;
      if (url) window.open(url, '_blank', 'noopener');
      container?.querySelector('.showcase-overlay')?.classList.remove('show');
      return;
    }

    if (cancelBtn) {
      e.preventDefault();
      e.stopPropagation();
      container?.querySelector('.showcase-overlay')?.classList.remove('show');
      return;
    }

    if (container && !e.target.closest('.showcase-overlay')) {
      e.preventDefault();
      document.querySelectorAll('.showcase-overlay.show').forEach(o => o.classList.remove('show'));
      container.querySelector('.showcase-overlay')?.classList.add('show');
    }
  });

  // Закрытие по Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.showcase-overlay.show').forEach(o => o.classList.remove('show'));
    }
  });

  // Первичный рендер
  renderPage();
})();
