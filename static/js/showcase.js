// Showcase Gallery with Auto-Sliding and Interactive Features

// Get showcase data from Django template (will be populated by backend)
let showcaseData = [];
// Tiny transparent placeholder to avoid network requests before lazy-load
const IMG_PLACEHOLDER = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';

// Fallback data if backend doesn't provide any
const fallbackShowcaseData = [
  {
    id: 1,
    category: 'portrait',
    title: 'Элегантный портрет',
    prompt: 'Cinematic portrait of elegant woman, soft studio lighting, 85mm lens, shallow depth of field, warm color grading, professional photography, high detail',
    images: [
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=80',
      'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800&q=80',
      'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&q=80'
    ]
  },
  {
    id: 2,
    category: 'fashion',
    title: 'Модный образ',
    prompt: 'High fashion editorial, dramatic lighting, luxury brand aesthetic, professional model, designer clothing, studio photography, vogue style, 50mm f/1.4',
    images: [
      'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&q=80',
      'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=80',
      'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&q=80'
    ]
  },
  {
    id: 3,
    category: 'art',
    title: 'Цифровое искусство',
    prompt: 'Digital art masterpiece, vibrant colors, surreal composition, artistic interpretation, creative lighting, fantasy elements, 4K resolution, trending on artstation',
    images: [
      'https://images.unsplash.com/photo-1549887534-1541e9326642?w=800&q=80',
      'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=800&q=80',
      'https://images.unsplash.com/photo-1547826039-bfc35e0f1ea8?w=800&q=80'
    ]
  },
  {
    id: 4,
    category: 'nature',
    title: 'Горный пейзаж',
    prompt: 'Majestic mountain landscape, golden hour lighting, dramatic clouds, wide angle lens, nature photography, HDR, breathtaking vista, professional landscape shot',
    images: [
      'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80',
      'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
      'https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=800&q=80'
    ]
  },
  {
    id: 5,
    category: 'fantasy',
    title: 'Фэнтези мир',
    prompt: 'Epic fantasy scene, magical atmosphere, ethereal lighting, mystical creatures, enchanted forest, cinematic composition, concept art style, highly detailed',
    images: [
      'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
      'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80',
      'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80'
    ]
  },
  {
    id: 6,
    category: 'portrait',
    title: 'Студийный портрет',
    prompt: 'Professional studio portrait, Rembrandt lighting, black background, dramatic shadows, 105mm lens, f/2.8, high contrast, editorial style photography',
    images: [
      'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&q=80',
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800&q=80',
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800&q=80'
    ]
  },
  {
    id: 7,
    category: 'fashion',
    title: 'Уличная мода',
    prompt: 'Street fashion photography, urban background, natural lighting, candid moment, trendy outfit, lifestyle aesthetic, 35mm lens, shallow DOF, modern style',
    images: [
      'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&q=80',
      'https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&q=80',
      'https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?w=800&q=80'
    ]
  },
  {
    id: 8,
    category: 'art',
    title: 'Абстрактная композиция',
    prompt: 'Abstract art composition, bold colors, geometric shapes, modern design, minimalist aesthetic, creative concept, digital illustration, contemporary art style',
    images: [
      'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=800&q=80',
      'https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=800&q=80',
      'https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=800&q=80'
    ]
  },
  {
    id: 9,
    category: 'nature',
    title: 'Океанский закат',
    prompt: 'Ocean sunset photography, golden hour, dramatic sky, long exposure, seascape, vibrant colors, peaceful atmosphere, professional nature shot, 24mm wide angle',
    images: [
      'https://images.unsplash.com/photo-1505142468610-359e7d316be0?w=800&q=80',
      'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
      'https://images.unsplash.com/photo-1439405326854-014607f694d7?w=800&q=80'
    ]
  },
  {
    id: 10,
    category: 'fantasy',
    title: 'Космическая одиссея',
    prompt: 'Space fantasy scene, nebula background, cosmic colors, sci-fi elements, futuristic aesthetic, cinematic lighting, epic scale, digital art masterpiece',
    images: [
      'https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=800&q=80',
      'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=800&q=80',
      'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&q=80'
    ]
  },
  {
    id: 11,
    category: 'portrait',
    title: 'Естественный свет',
    prompt: 'Natural light portrait, window lighting, soft shadows, authentic emotion, candid photography, 50mm f/1.8, warm tones, intimate atmosphere, lifestyle shot',
    images: [
      'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&q=80',
      'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=800&q=80',
      'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&q=80'
    ]
  },
  {
    id: 12,
    category: 'fashion',
    title: 'Высокая мода',
    prompt: 'Haute couture fashion, luxury brand campaign, professional styling, dramatic pose, editorial lighting, designer collection, runway aesthetic, 70mm medium format',
    images: [
      'https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&q=80',
      'https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=800&q=80',
      'https://images.unsplash.com/photo-1487222477894-8943e31ef7b2?w=800&q=80'
    ]
  },
  {
    id: 13,
    category: 'art',
    title: 'Сюрреализм',
    prompt: 'Surrealist artwork, dreamlike atmosphere, impossible geometry, creative concept, artistic vision, vibrant palette, imaginative composition, digital painting',
    images: [
      'https://images.unsplash.com/photo-1536924940846-227afb31e2a5?w=800&q=80',
      'https://images.unsplash.com/photo-1533158326339-7f3cf2404354?w=800&q=80',
      'https://images.unsplash.com/photo-1549887534-1541e9326642?w=800&q=80'
    ]
  },
  {
    id: 14,
    category: 'nature',
    title: 'Лесная тропа',
    prompt: 'Forest path photography, morning mist, soft natural light, green foliage, peaceful atmosphere, nature walk, wide angle landscape, serene environment',
    images: [
      'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
      'https://images.unsplash.com/photo-1511497584788-876760111969?w=800&q=80',
      'https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?w=800&q=80'
    ]
  },
  {
    id: 15,
    category: 'fantasy',
    title: 'Драконий замок',
    prompt: 'Fantasy castle scene, dragon flying, medieval architecture, epic scale, dramatic sky, magical atmosphere, concept art quality, highly detailed illustration',
    images: [
      'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
      'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&q=80',
      'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80'
    ]
  },
  {
    id: 16,
    category: 'portrait',
    title: 'Креативный портрет',
    prompt: 'Creative portrait photography, colored gels, experimental lighting, artistic expression, unique composition, bold colors, modern aesthetic, 85mm f/1.4',
    images: [
      'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&q=80',
      'https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=800&q=80',
      'https://images.unsplash.com/photo-1520813792240-56fc4a3765a7?w=800&q=80'
    ]
  },
  {
    id: 17,
    category: 'fashion',
    title: 'Минимализм в моде',
    prompt: 'Minimalist fashion photography, clean background, simple composition, elegant styling, neutral colors, modern aesthetic, professional lighting, editorial quality',
    images: [
      'https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=800&q=80',
      'https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=800&q=80',
      'https://images.unsplash.com/photo-1467632499275-7a693a761056?w=800&q=80'
    ]
  },
  {
    id: 18,
    category: 'art',
    title: 'Неоновые огни',
    prompt: 'Neon lights artwork, cyberpunk aesthetic, vibrant colors, urban night scene, futuristic vibe, digital art, glowing effects, contemporary style, 4K quality',
    images: [
      'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=800&q=80',
      'https://images.unsplash.com/photo-1514539079130-25950c84af65?w=800&q=80',
      'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80'
    ]
  },
  {
    id: 19,
    category: 'nature',
    title: 'Водопад в джунглях',
    prompt: 'Jungle waterfall photography, lush vegetation, tropical paradise, long exposure water, natural beauty, adventure photography, wide angle shot, vibrant greens',
    images: [
      'https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80',
      'https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&q=80',
      'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=800&q=80'
    ]
  },
  {
    id: 20,
    category: 'fantasy',
    title: 'Магический портал',
    prompt: 'Magical portal scene, mystical energy, glowing effects, fantasy landscape, otherworldly atmosphere, epic composition, concept art style, cinematic lighting',
    images: [
      'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
      'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80',
      'https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=800&q=80'
    ]
  }
];

class ShowcaseGallery {
  constructor(data = null) {
    // Use provided data, or fallback data if none provided
    this.data = data && data.length > 0 ? data : fallbackShowcaseData;
    this.currentCategory = 'all';
    this.sliders = new Map();
    this.autoPlayIntervals = new Map();
    this.autoPlayDelay = 4000; // 4 seconds
    // Disable slide animations and autoplay on mobile devices
    this.isMobile = (window.matchMedia && (window.matchMedia('(max-width: 640px)').matches || window.matchMedia('(pointer: coarse)').matches)) || (window.innerWidth <= 640);
    this.disableAnimations = !!this.isMobile;

    // Two-rows initial render: compute columns by breakpoints of #showcaseGrid (1,2,3,4)
    (() => {
      try {
        const w = window.innerWidth || 0;
        // grid: 1 (mobile), 2 (>=480px), 3 (>=768px), 4 (>=1024px)
        const cols = (w >= 1024) ? 4 : (w >= 768) ? 3 : (w >= 480) ? 2 : 1;
        const twoRows = Math.max(1, cols) * 2;
        this.BATCH_SIZE = twoRows;                 // render only two rows initially
        this.ABOVE_THE_FOLD_COUNT = Math.min(twoRows, 6);
        this.EAGER_COUNT = Math.min(twoRows, 6);
      } catch (_) { }
    })();

    // Performance: capped initial render to 12; rest via "Показать ещё"
    this.BATCH_SIZE = 12;
    this.ABOVE_THE_FOLD_COUNT = 12;
    this.EAGER_COUNT = Math.min(4, this.BATCH_SIZE);
    this.renderedCount = 0;
    this.filteredData = [];
    // Persist revealed count per category to keep state stable across switches
    this.revealedByCat = this.loadRevealedByCat ? this.loadRevealedByCat() : {};

    // Lazy loading: hydrate images when card nears viewport
    this.io = ('IntersectionObserver' in window) ? new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          this.loadCardFirstImage(en.target, 'low');
          this._hydrateAllImages(en.target);
          this.io.unobserve(en.target);
        }
      });
    }, { rootMargin: '300px' }) : null;

    // Автовоспроизведение только для видимых карточек
    this.playObserver = ('IntersectionObserver' in window) ? new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const card = entry.target;
        const id = card && card.dataset ? card.dataset.id : null;
        if (!id) return;
        if (entry.isIntersecting) {
          this.startAutoPlay(id);
        } else {
          this.stopAutoPlay(id);
        }
      });
    }, { threshold: 0.6 }) : null;

    this.init();
  }

  init() {
    // Сначала читаем ?scat и подсвечиваем фильтр, затем рендер
    this.setupFilters();
    this.renderShowcase();
    this.setupPromptInsertion();
  }

  renderShowcase() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    // Reset grid and state
    if (this.io) { try { this.io.disconnect(); } catch (_) { } }
    grid.innerHTML = '';
    this.sliders.clear();
    this.stopAllAutoPlay();
    if (this.playObserver) {
      this.playObserver.disconnect();
    }

    // Fail-safe: never allow a single-category dataset to stick after reload
    let fullData = this.data;
    try {
      const cachedRaw = localStorage.getItem('showcase.dataset');
      const cached = cachedRaw ? JSON.parse(cachedRaw) : null;
      const catCount = (arr) => {
        try { return new Set((arr || []).map(i => i && i.category)).size || 0; } catch (_) { return 0; }
      };
      const candidates = [];
      if (Array.isArray(fullData) && fullData.length) {
        candidates.push({ data: fullData, cats: catCount(fullData) });
      }
      if (cached && Array.isArray(cached) && cached.length) {
        candidates.push({ data: cached, cats: catCount(cached) });
      }
      candidates.push({ data: fallbackShowcaseData, cats: catCount(fallbackShowcaseData) });
      candidates.sort((a, b) => (b.cats - a.cats) || ((b.data?.length || 0) - (a.data?.length || 0)));
      fullData = candidates[0]?.data || fallbackShowcaseData;
      this.data = fullData;
    } catch (_) { /* ignore */ }

    this.filteredData = this.currentCategory === 'all'
      ? fullData
      : fullData.filter(item => item.category === this.currentCategory);

    this.renderedCount = 0;

    // Initial render: показываем только 2 ряда. Убираем следы старой бесконечной прокрутки.
    try {
      if (this.sentinelObserver) this.sentinelObserver.disconnect();
      document.getElementById('showcaseSentinel')?.remove();
    } catch (_) { }

    // Рендерим все карточки — без "Показать ещё"
    const target = this.filteredData.length;
    while (this.renderedCount < target) {
      this.renderNextBatch();
    }
    // Горизонтальный скроллер с навигацией стрелками, как было ранее
    this.setupHorizontalScroller();
  }

  createShowcaseCard(item) {
    const article = document.createElement('article');
    // Single row horizontal scroller: prevent shrinking and set responsive basis so 3 cards visible on desktop
    article.className = 'showcase-card showcase-item shrink-0 basis-full xs:basis-1/2 md:basis-1/3 lg:basis-1/3';
    // Keep card height strict and flush (no offscreen reservation)
    try {
      article.style.contentVisibility = 'visible';
      article.style.containIntrinsicSize = '';
    } catch (_) { }
    article.dataset.category = item.category;
    article.dataset.id = item.id;

    const categoryNames = {
      portrait: 'Портреты',
      fashion: 'Мода',
      art: 'Арт',
      nature: 'Природа',
      fantasy: 'Фэнтези',
      misc: 'Разное'
    };

    // Lightweight URL optimizer for known CDNs (e.g., Unsplash) to serve compressed WEBP
    const optimize = (u) => {
      try {
        const url = new URL(u, window.location.origin);
        if (url.hostname.includes('images.unsplash.com')) {
          // Prefer WEBP, moderate quality, and limit width for card thumbnails
          url.searchParams.set('auto', 'format');
          url.searchParams.set('fit', 'max');
          const w = parseInt(url.searchParams.get('w') || '0', 10);
          if (!w || w > 640) url.searchParams.set('w', '640');
          if (!url.searchParams.get('q')) url.searchParams.set('q', '70');
          url.searchParams.set('fm', 'webp');
          return url.toString();
        }
        return u;
      } catch (_) { return u; }
    };

    const hasMultipleImages = item.images && item.images.length > 1;

    article.innerHTML = `
      <div class="card overflow-hidden transition-all duration-300">
        <!-- Image Slider -->
        <div class="showcase-slider">
          <div class="showcase-slider-track">
            ${item.images.map((img, idx) => {
      const isObj = typeof img === 'object' && img !== null;
      const urlThumb = isObj ? (img.thumb || img.full) : img;
      const urlFull = isObj ? (img.full || img.thumb) : img;
      return `
              <img
                src="${IMG_PLACEHOLDER}"
                data-src="${optimize(urlThumb)}"
                data-full="${optimize(urlFull)}"
                alt="${item.title}"
                class="showcase-slider-image"
                loading="lazy"
                decoding="async"
                fetchpriority="low"
                width="800"
                height="1067"
                sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, (min-width: 480px) 50vw, 100vw"
                referrerpolicy="no-referrer"
                data-index="${idx}"
              >
              `;
    }).join('')}
          </div>

          <!-- Category Badge -->
          <div class="showcase-category">${categoryNames[item.category] || item.category}</div>

          ${hasMultipleImages ? `
          <!-- Navigation Arrows -->
          <button class="showcase-nav showcase-nav-prev" aria-label="Предыдущее изображение">
            <svg viewBox="0 0 24 24">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
          <button class="showcase-nav showcase-nav-next" aria-label="Следующее изображение">
            <svg viewBox="0 0 24 24">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>

          <!-- Dots Indicator -->
          <div class="showcase-dots">
            ${item.images.map((_, index) => `
              <button class="showcase-dot ${index === 0 ? 'active' : ''}" data-index="${index}" aria-label="Изображение ${index + 1}"></button>
            `).join('')}
          </div>
          ` : ''}
        </div>

        <!-- Card Content -->
        <div class="showcase-content">
          <h3 class="showcase-title">${item.title}</h3>

          <!-- Prompt header -->
          <div class="showcase-prompt-header" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9h8M8 13h5M4 6h16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2z"/>
            </svg>
            <span>Промпт</span>
          </div>

          <div class="showcase-prompt-box">
            <p class="showcase-prompt">${item.prompt || 'Промпт не указан'}</p>
          </div>

          <button class="showcase-use-btn" data-prompt="${this.escapeHtml(item.prompt)}" aria-label="Использовать промпт">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
            </svg>
            <span>Использовать промпт</span>
          </button>
        </div>
      </div>
    `;

    return article;
  }

  // Lazy-load helpers
  loadCardFirstImage(card, priority = 'low') {
    const firstImg = card.querySelector('.showcase-slider-image[data-index="0"]');
    if (firstImg && firstImg.dataset.src && firstImg.src !== firstImg.dataset.src) {
      this.lazyLoadImage(firstImg, priority);
    }
  }

  lazyLoadImage(img, priority = 'low') {
    if (!img || !img.dataset || !img.dataset.src) return;
    img.src = img.dataset.src;
    img.removeAttribute('data-src');
    if (priority === 'high') {
      img.setAttribute('loading', 'eager');
      img.setAttribute('fetchpriority', 'high');
    } else {
      img.setAttribute('loading', 'lazy');
      img.setAttribute('fetchpriority', 'low');
    }
    img.setAttribute('decoding', 'async');
  }

  _hydrateAllImages(card) {
    try {
      const imgs = card.querySelectorAll('.showcase-slider-image');
      imgs.forEach(img => {
        if (img.dataset && img.dataset.src) {
          this.lazyLoadImage(img, 'low');
        }
      });
    } catch (_) {}
  }

  ensureImageLoaded(state, index) {
    if (!state) return;
    const imgs = state.slider.querySelectorAll('.showcase-slider-image');
    const img = imgs[index];
    if (!img) return;
    if (img.dataset && img.dataset.src) {
      this.lazyLoadImage(img, 'low');
    }
    try { img.decode && img.decode().catch(() => { }); } catch (_) { }
  }

  renderNextBatch() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    const start = this.renderedCount;
    const end = Math.min(start + this.BATCH_SIZE, this.filteredData.length);

    for (let i = start; i < end; i++) {
      const item = this.filteredData[i];
      const card = this.createShowcaseCard(item);
      try { card.style.scrollSnapAlign = 'start'; } catch (_) { }
      grid.appendChild(card);
      if (start === 0 && i < this.EAGER_COUNT) {
        // Eager-load first images for the first visible cards
        this.loadCardFirstImage(card, 'high');
      } else if (this.io) {
        this.io.observe(card);
      } else {
        // Fallback: load first image immediately
        this.loadCardFirstImage(card, 'low');
      }
    }

    this.renderedCount = end;
    // Persist revealed count for current category
    try {
      if (!this.revealedByCat) this.revealedByCat = {};
      this.revealedByCat[this.currentCategory || 'all'] = this.renderedCount;
      this.saveRevealedByCat && this.saveRevealedByCat();
    } catch (_) { }

    if (this.loadMoreBtn) {
      this.loadMoreBtn.style.display = this.renderedCount < this.filteredData.length ? '' : 'none';
    }

    // Initialize sliders for newly added cards
    this.initializeSliders();
  }

  // Кнопка «Показать ещё» — использует кнопку из шаблона, рендерит следующую партию
  createLoadMoreButton() {
    const btn = document.getElementById('showcaseLoadMore');
    if (!btn) { this.loadMoreBtn = null; return; }
    this.loadMoreBtn = btn;
    btn.classList.toggle('hidden', this.renderedCount >= this.filteredData.length);
    if (!btn._bound) {
      btn.addEventListener('click', () => this.renderNextBatch(), { passive: true });
      btn._bound = true;
    }
  }

  // Настройка 1 ряда с горизонтальным скроллом и кнопками "Назад" / "Смотреть ещё"
  setupHorizontalScroller() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    // Превращаем в горизонтальный скроллер
    try {
      // inline-стили переопределяют tailwind grid-классы из шаблона
      grid.style.display = 'flex';
      grid.style.flexWrap = 'nowrap';
      grid.style.overflowX = 'auto';
      grid.style.overflowY = 'hidden';
      grid.style.scrollBehavior = 'smooth';
      grid.style.gap = '0.75rem'; // близко к gap-3
      grid.style.scrollSnapType = 'x proximity';
      grid.classList.add('no-scrollbar');
      grid.setAttribute('role', 'region');
      grid.setAttribute('aria-label', 'Примеры результатов (горизонтальная лента)');
    } catch (_) { }

    // Обёртка для кнопок-стрелок: поверх ленты, адаптивные стрелки слева/справа
    // Удаляем старую нижнюю навигацию, если вдруг осталась
    try { document.getElementById('showcaseHNav')?.remove(); } catch (_) {}
    // Готовим обёртку без скролла для позиционирования стрелок
    let wrap = grid.parentElement && grid.parentElement.id === 'showcaseTrackWrap' ? grid.parentElement : null;
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.id = 'showcaseTrackWrap';
      wrap.className = 'relative';
      grid.insertAdjacentElement('beforebegin', wrap);
      wrap.appendChild(grid);
    }
    // Стрелки в стиле сайта (dark/light-friendly)
    const makeArrow = (dir) => {
      const btn = document.createElement('button');
      btn.id = dir === 'prev' ? 'showcasePrevBtn' : 'showcaseNextBtn';
      btn.type = 'button';
      btn.className = [
        'absolute top-1/2 -translate-y-1/2 z-10 inline-flex items-center justify-center',
        'rounded-full border border-[var(--bord)] bg-[var(--bg-card)]/80 text-[var(--text)]',
        'hover:border-primary/60 hover:text-primary shadow backdrop-blur-sm',
        'w-8 h-8 sm:w-10 sm:h-10 focus:outline-none focus:ring-2 focus:ring-primary/50'
      ].join(' ');
      if (dir === 'prev') {
        btn.classList.add('left-2');
        btn.setAttribute('aria-label', 'Назад');
        btn.innerHTML = `
          <svg class="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 18l-6-6 6-6"/>
          </svg>
        `;
      } else {
        btn.classList.add('right-2');
        btn.setAttribute('aria-label', 'Вперёд');
        btn.innerHTML = `
          <svg class="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 18l6-6-6-6"/>
          </svg>
        `;
      }
      return btn;
    };
    // Создаём/обновляем стрелки
    let prev = document.getElementById('showcasePrevBtn');
    if (!prev) { prev = makeArrow('prev'); wrap.appendChild(prev); }
    let next = document.getElementById('showcaseNextBtn');
    if (!next) { next = makeArrow('next'); wrap.appendChild(next); }

    const prevBtn = document.getElementById('showcasePrevBtn');
    const nextBtn = document.getElementById('showcaseNextBtn');

    const updateNav = () => {
      const maxScrollLeft = grid.scrollWidth - grid.clientWidth - 4;
      // видимость кнопок по положению скролла
      const atStart = grid.scrollLeft <= 4;
      const atEnd = grid.scrollLeft >= maxScrollLeft;

      if (prevBtn) {
        // Hide "Назад" until user scrolls
        prevBtn.style.display = atStart ? 'none' : '';
        prevBtn.style.opacity = atStart ? '0' : '1';
        prevBtn.style.pointerEvents = atStart ? 'none' : 'auto';
      }
      if (nextBtn) {
        // Keep "Смотреть ещё" visible; disable at end
        nextBtn.style.opacity = atEnd ? '0.5' : '1';
        nextBtn.style.pointerEvents = atEnd ? 'none' : 'auto';
      }
    };

    const scrollAmount = () => {
      // пролистываем почти на экран
      return Math.max(240, Math.floor(grid.clientWidth * 0.9));
    };

    // Прокрутка по кнопкам
    prevBtn?.addEventListener('click', () => {
      grid.scrollBy({ left: -scrollAmount(), behavior: 'smooth' });
    });
    nextBtn?.addEventListener('click', () => {
      grid.scrollBy({ left: scrollAmount(), behavior: 'smooth' });
    });

    // Адаптивная ширина карточек: ровно 1/2 на xs, 1/3 на md+, 1/1 на очень маленьких
    const setCardSizes = () => {
      try {
        const cards = grid.querySelectorAll('.showcase-card');
        if (!cards.length) return;
        const w = grid.clientWidth || window.innerWidth || 0;

        // Кол-во колонок по брейкпоинтам: <480 — 1, <768 — 2, иначе — 3
        let cols = 3;
        if (w < 480) cols = 1;
        else if (w < 768) cols = 2;

        // Учитываем gap контейнера
        const cs = getComputedStyle(grid);
        const gap = parseFloat(cs.columnGap || cs.gap || '0') || 0;
        const totalGap = gap * Math.max(0, cols - 1);

        // Вычисляем базис с учётом gap и минимальной ширины карточки
        const scale = 0.8; // уменьшить карточки ~на 20%
        const basisPx = Math.max(180, Math.floor((w - totalGap) / cols) * scale);

        cards.forEach(card => {
          card.style.flex = `0 0 ${basisPx}px`;
          card.style.maxWidth = `${basisPx}px`;
          card.style.scrollSnapAlign = 'start';
        });
      } catch(_) {}
    };

    // Обновление состояния при скролле и ресайзе
    grid.addEventListener('scroll', updateNav, { passive: true });
    window.addEventListener('resize', () => {
      // после изменения ширины сразу актуализируем
      setCardSizes();
      updateNav();
    });

    // Сброс в начало при ререндере
    try { grid.scrollLeft = 0; } catch (_) { }
    // Первичная инициализация
    setCardSizes();
    updateNav();
  }

  initializeSliders() {
    const cards = document.querySelectorAll('.showcase-card');

    cards.forEach(card => {
      const id = card.dataset.id;
      if (this.sliders.has(id)) return;

      const slider = card.querySelector('.showcase-slider-track');
      const prevBtn = card.querySelector('.showcase-nav-prev');
      const nextBtn = card.querySelector('.showcase-nav-next');
      const dots = card.querySelectorAll('.showcase-dot');
      const images = card.querySelectorAll('.showcase-slider-image');
      try { slider && (slider.style.willChange = 'transform'); } catch (_) { }
      // Надёжная обработка ошибок загрузки изображений
      images.forEach(img => {
        img.addEventListener('error', () => {
          try {
            if (img.dataset && img.dataset.full) {
              img.src = img.dataset.full;
              img.removeAttribute('data-full');
            } else {
              img.src = IMG_PLACEHOLDER;
            }
          } catch (_) { }
        });
      });

      if (!slider || images.length === 0) return;
      if (this.disableAnimations) { try { slider.style.transition = 'none'; } catch (_) { } }

      const sliderState = {
        currentIndex: 0,
        totalImages: images.length,
        slider: slider,
        dots: dots,
        card: card
      };

      this.sliders.set(id, sliderState);
      // Гарантированно подгружаем первый кадр
      this.ensureImageLoaded(sliderState, 0);
      // Запускаем автоплей только когда карточка в видимой области
      if (this.playObserver) {
        this.playObserver.observe(card);
      } else {
        this.startAutoPlay(id);
      }

      // Navigation buttons
      prevBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        this.stopAutoPlay(id);
        this.goToPrevious(id);
        this.startAutoPlay(id);
      });

      nextBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        this.stopAutoPlay(id);
        this.goToNext(id);
        this.startAutoPlay(id);
      });

      // Dots navigation
      dots.forEach((dot, index) => {
        dot.addEventListener('click', (e) => {
          e.stopPropagation();
          this.stopAutoPlay(id);
          this.goToSlide(id, index);
          this.startAutoPlay(id);
        });
      });

      // Pause on hover
      card.addEventListener('mouseenter', () => this.stopAutoPlay(id));
      card.addEventListener('mouseleave', () => this.startAutoPlay(id));

      // Touch support
      let touchStartX = 0;
      let touchEndX = 0;

      slider.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        this.stopAutoPlay(id);
      }, { passive: true });

      slider.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        this.handleSwipe(id, touchStartX, touchEndX);
        this.startAutoPlay(id);
      }, { passive: true });

      // Start auto-play (only if no IntersectionObserver support)
      if (!this.playObserver) {
        this.startAutoPlay(id);
      }
    });
  }

  goToSlide(id, index) {
    const state = this.sliders.get(id);
    if (!state) return;

    const total = state.totalImages;

    // Ensure current and adjacent images are ready for smooth transition
    this.ensureImageLoaded(state, index);
    if (total > 1) {
      this.ensureImageLoaded(state, (index + 1) % total);
      this.ensureImageLoaded(state, (index - 1 + total) % total);
    }

    state.currentIndex = index;
    const offset = -index * 100;
    state.slider.style.transform = `translateX(${offset}%)`;

    // Update dots
    state.dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  }

  goToNext(id) {
    const state = this.sliders.get(id);
    if (!state) return;

    const nextIndex = (state.currentIndex + 1) % state.totalImages;
    this.goToSlide(id, nextIndex);
  }

  goToPrevious(id) {
    const state = this.sliders.get(id);
    if (!state) return;

    const prevIndex = (state.currentIndex - 1 + state.totalImages) % state.totalImages;
    this.goToSlide(id, prevIndex);
  }

  handleSwipe(id, startX, endX) {
    const threshold = 50;
    const diff = startX - endX;

    if (Math.abs(diff) > threshold) {
      if (diff > 0) {
        this.goToNext(id);
      } else {
        this.goToPrevious(id);
      }
    }
  }

  startAutoPlay(id) {
    if (this.disableAnimations) return;
    this.stopAutoPlay(id);
    const interval = setInterval(() => {
      this.goToNext(id);
    }, this.autoPlayDelay);
    this.autoPlayIntervals.set(id, interval);
  }

  stopAutoPlay(id) {
    const interval = this.autoPlayIntervals.get(id);
    if (interval) {
      clearInterval(interval);
      this.autoPlayIntervals.delete(id);
    }
  }

  // Apply filter and re-render in-place (client-side; no page reload)
  applyFilter(category) {
    this.currentCategory = category || 'all';
    this.setActiveFilterUI(this.currentCategory);
    // Update URL query param without reload to preserve state
    try {
      const usp = new URLSearchParams(window.location.search);
      this.currentCategory === 'all' ? usp.delete('scat') : usp.set('scat', this.currentCategory);
      history.replaceState(null, '', `${location.pathname}${usp.toString() ? '?' + usp.toString() : ''}`);
    } catch (_) { }
    this.renderShowcase();
    // Smooth scroll to the grid so user sees fresh content
    try { document.getElementById('showcaseGrid')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_) { }
  }

  // Highlight active filter pill
  setActiveFilterUI(active) {
    const filterButtons = document.querySelectorAll('.js-showcase-filter');
    filterButtons.forEach(btn => {
      const category = btn.dataset.category || 'all';
      const on = (active === 'all' && category === 'all') || active === category;
      btn.classList.toggle('bg-primary/15', on);
      btn.classList.toggle('text-primary', on);
      btn.classList.toggle('border-primary/30', on);
    });
  }

  // LocalStorage helpers for stable "revealed" state per category
  loadRevealedByCat() {
    try {
      const raw = localStorage.getItem('showcase.revealed');
      const obj = raw ? JSON.parse(raw) : {};
      return (obj && typeof obj === 'object') ? obj : {};
    } catch (_) { return {}; }
  }
  saveRevealedByCat() {
    try { localStorage.setItem('showcase.revealed', JSON.stringify(this.revealedByCat || {})); } catch (_) { }
  }
  getInitialRevealCount() {
    // Default: two rows (BATCH_SIZE). If user already revealed more for a category,
    // use the saved count to avoid losing results when switching back.
    const saved = (this.revealedByCat && this.revealedByCat[this.currentCategory || 'all']) || 0;
    const baseline = this.BATCH_SIZE || 8;
    return Math.max(baseline, saved);
  }

  setupFilters() {
    // Уважать текущий ?scat; по умолчанию — 'all'
    try {
      const usp = new URLSearchParams(window.location.search);
      const scat = (usp.get('scat') || 'all').trim();
      this.currentCategory = scat || 'all';
    } catch (_) {
      this.currentCategory = 'all';
    }
    this.setActiveFilterUI(this.currentCategory);

    // Delegate click once for robustness (anchors or buttons, nested icons, etc.)
    if (this._filtersBound) return;
    this._filtersBound = true;

    document.addEventListener('click', (e) => {
      const el = e.target && e.target.closest ? e.target.closest('.js-showcase-filter') : null;
      if (!el) return;
      // Prevent any default navigation and other handlers
      e.preventDefault();
      e.stopPropagation();
      const cat = el.dataset.category || 'all';
      if (cat === this.currentCategory) return;
      this.applyFilter(cat);
    }, { passive: false, capture: true });
  }

  setupPromptInsertion() {
    document.addEventListener('click', (e) => {
      // Toggle prompt expansion
      const promptEl = e.target.closest('.showcase-prompt');
      if (promptEl) {
        promptEl.classList.toggle('expanded');
        e.stopPropagation();
        return;
      }

      /* copy button removed by request */
      // Insert prompt button
      const btn = e.target.closest('.showcase-use-btn');
      if (!btn) return;

      const prompt = btn.dataset.prompt;
      const promptField = document.getElementById('prompt');

      if (promptField && prompt) {
        promptField.value = prompt;
        promptField.focus();

        // Smooth scroll to form
        const form = promptField.closest('form');
        if (form) {
          form.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // Visual feedback
        btn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          <span>Промпт добавлен!</span>
        `;

        setTimeout(() => {
          btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
            </svg>
            <span>Использовать промпт</span>
          `;
        }, 2000);
      }
    });
  }

  stopAllAutoPlay() {
    this.autoPlayIntervals.forEach((interval, id) => {
      clearInterval(interval);
    });
    this.autoPlayIntervals.clear();
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Function to initialize gallery with data from Django
function initShowcaseGallery(djangoData) {
  // Choose the most complete dataset (avoid "stuck" single-category data after reload)
  const catCount = (arr) => {
    try { return new Set((arr || []).map(i => i && i.category)).size || 0; } catch (_) { return 0; }
  };
  const isUsableFull = (arr) => Array.isArray(arr) && arr.length >= 8 && catCount(arr) > 1;

  try {
    const cachedRaw = localStorage.getItem('showcase.dataset');
    const cached = cachedRaw ? JSON.parse(cachedRaw) : null;

    const candidates = [];
    if (cached && Array.isArray(cached) && cached.length > 0) {
      candidates.push({ name: 'cache', data: cached, cats: catCount(cached) });
    }
    if (djangoData && Array.isArray(djangoData) && djangoData.length > 0) {
      candidates.push({ name: 'django', data: djangoData, cats: catCount(djangoData) });
    }
    // fallback always exists
    candidates.push({ name: 'fallback', data: fallbackShowcaseData, cats: catCount(fallbackShowcaseData) });

    // Prefer by more categories, then by length
    candidates.sort((a, b) => (b.cats - a.cats) || ((b.data?.length || 0) - (a.data?.length || 0)));
    const preferred = candidates[0]?.data || fallbackShowcaseData;
    console.log('Dataset pick:', candidates[0]?.name, 'cats:', candidates[0]?.cats, 'len:', preferred.length);

    showcaseData = preferred;

    // Only refresh cache when we have a "full" dataset (multi-category and decent size)
    try {
      if (isUsableFull(preferred)) {
        localStorage.setItem('showcase.dataset', JSON.stringify(preferred));
      }
    } catch (_) { /* ignore quota/privacy */ }
  } catch (_) {
    console.log('Dataset selection failed, using provided/fallback');
    showcaseData = (djangoData && Array.isArray(djangoData) && djangoData.length > 0) ? djangoData : fallbackShowcaseData;
  }

  new ShowcaseGallery(showcaseData);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    // Check if Django provided data via window object
    const djangoData = window.showcaseGalleryData;
    initShowcaseGallery(djangoData);
  });
} else {
  const djangoData = window.showcaseGalleryData;
  initShowcaseGallery(djangoData);
}

// Export for external use
window.initShowcaseGallery = initShowcaseGallery;
