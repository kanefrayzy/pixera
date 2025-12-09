// Showcase Gallery - Ultra-Optimized Version
// Features: WebP support, progressive loading, intersection observer, minimal reflows

let showcaseData = [];
const IMG_PLACEHOLDER = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1067"%3E%3Crect fill="%23f0f0f0"/%3E%3C/svg%3E';

// Detect WebP support
let supportsWebP = false;
(function() {
  const img = new Image();
  img.onload = img.onerror = () => { supportsWebP = img.height === 2; };
  img.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
})();

// Fallback showcase data
const fallbackShowcaseData = [
  {
    id: 1,
    category: 'portrait',
    title: 'Элегантный портрет',
    prompt: 'Cinematic portrait of elegant woman, soft studio lighting, 85mm lens, shallow depth of field, warm color grading, professional photography, high detail',
    images: [
      { thumb: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=75', full: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=80' }
    ]
  },
  {
    id: 2,
    category: 'fashion',
    title: 'Модный образ',
    prompt: 'High fashion editorial, dramatic lighting, luxury brand aesthetic, professional model, designer clothing, studio photography, vogue style, 50mm f/1.4',
    images: [
      { thumb: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&q=75', full: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&q=80' }
    ]
  }
];

class ShowcaseGallery {
  constructor(data = null) {
    this.data = data && data.length > 0 ? data : fallbackShowcaseData;
    this.currentCategory = 'all';
    this.sliders = new Map();
    this.autoPlayIntervals = new Map();
    this.autoPlayDelay = 4000;

    // Mobile detection
    this.isMobile = window.innerWidth <= 640 || ('ontouchstart' in window);
    this.disableAnimations = this.isMobile;

    // Calculate initial batch size (2 rows)
    const w = window.innerWidth;
    const cols = w >= 1024 ? 4 : w >= 768 ? 3 : w >= 480 ? 2 : 1;
    this.BATCH_SIZE = cols * 2;
    this.EAGER_COUNT = Math.min(cols * 2, 6);

    this.renderedCount = 0;
    this.filteredData = [];

    // Intersection Observer for lazy loading
    this.io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          this.loadCardFirstImage(entry.target);
          this.io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '400px 0px' });

    // Autoplay observer
    this.playObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const id = entry.target.dataset.id;
        if (!id) return;
        entry.isIntersecting ? this.startAutoPlay(id) : this.stopAutoPlay(id);
      });
    }, { threshold: 0.5 });

    this.init();
  }

  init() {
    this.renderShowcase();
    this.setupFilters();
    this.setupPromptInsertion();
  }

  renderShowcase() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    grid.innerHTML = '';
    this.sliders.clear();
    this.stopAllAutoPlay();
    this.playObserver?.disconnect();

    this.filteredData = this.currentCategory === 'all'
      ? this.data
      : this.data.filter(item => item.category === this.currentCategory);

    this.renderedCount = 0;
    this.renderNextBatch();
    this.createLoadMoreButton();
  }

  createShowcaseCard(item) {
    const article = document.createElement('article');
    article.className = 'showcase-card showcase-item';
    article.style.contentVisibility = 'auto';
    article.style.containIntrinsicSize = '600px';
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

    const hasMultiple = item.images && item.images.length > 1;

    // Build images HTML with optimized attributes
    const imagesHTML = item.images.map((img, idx) => {
      const isObj = typeof img === 'object';
      const thumb = isObj ? (img.thumb || img.full) : img;
      const full = isObj ? (img.full || img.thumb) : img;

      return `<img
        src="${IMG_PLACEHOLDER}"
        data-src="${thumb}"
        data-full="${full}"
        alt="${item.title}"
        class="showcase-slider-image"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
        width="800"
        height="1067"
        data-index="${idx}">`;
    }).join('');

    article.innerHTML = `
      <div class="card overflow-hidden transition-all duration-300">
        <div class="showcase-slider">
          <div class="showcase-slider-track">${imagesHTML}</div>
          <div class="showcase-category">${categoryNames[item.category] || item.category}</div>
          ${hasMultiple ? `
          <button class="showcase-nav showcase-nav-prev" aria-label="Предыдущее">
            <svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <button class="showcase-nav showcase-nav-next" aria-label="Следующее">
            <svg viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
          </button>
          <div class="showcase-dots">
            ${item.images.map((_, i) => `<button class="showcase-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></button>`).join('')}
          </div>
          ` : ''}
        </div>
        <div class="showcase-content">
          <h3 class="showcase-title">${item.title}</h3>
          <div class="showcase-prompt-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9h8M8 13h5M4 6h16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2z"/>
            </svg>
            <span>Промпт</span>
          </div>
          <div class="showcase-prompt-box">
            <p class="showcase-prompt">${item.prompt || 'Промпт не указан'}</p>
          </div>
          <button class="showcase-use-btn" data-prompt="${this.escapeHtml(item.prompt)}">
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

  loadCardFirstImage(card, priority = 'low') {
    const img = card.querySelector('.showcase-slider-image[data-index="0"]');
    if (img?.dataset.src) {
      this.lazyLoadImage(img, priority);
    }
  }

  lazyLoadImage(img, priority = 'low') {
    if (!img?.dataset?.src) return;

    // Use requestIdleCallback for non-critical images
    const load = () => {
      img.src = img.dataset.src;
      delete img.dataset.src;
      img.loading = priority === 'high' ? 'eager' : 'lazy';
      img.fetchpriority = priority;
      img.decoding = 'async';
    };

    if (priority === 'high' || !('requestIdleCallback' in window)) {
      load();
    } else {
      requestIdleCallback(load, { timeout: 2000 });
    }
  }

  ensureImageLoaded(state, index) {
    const img = state.slider.querySelectorAll('.showcase-slider-image')[index];
    if (img?.dataset?.src) {
      this.lazyLoadImage(img, 'low');
    }
  }

  renderNextBatch() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    const start = this.renderedCount;
    const end = Math.min(start + this.BATCH_SIZE, this.filteredData.length);

    // Use DocumentFragment for better performance
    const fragment = document.createDocumentFragment();

    for (let i = start; i < end; i++) {
      const card = this.createShowcaseCard(this.filteredData[i]);
      fragment.appendChild(card);

      if (start === 0 && i < this.EAGER_COUNT) {
        // Eager load first visible cards
        requestAnimationFrame(() => this.loadCardFirstImage(card, 'high'));
      } else {
        this.io.observe(card);
      }
    }

    grid.appendChild(fragment);
    this.renderedCount = end;

    if (this.loadMoreBtn) {
      this.loadMoreBtn.style.display = this.renderedCount < this.filteredData.length ? '' : 'none';
    }

    // Initialize sliders in next frame to avoid blocking
    requestAnimationFrame(() => this.initializeSliders());
  }

  createLoadMoreButton() {
    const grid = document.getElementById('showcaseGrid');
    if (!grid) return;

    let btn = document.getElementById('showcaseLoadMore');
    if (!btn) {
      const wrap = document.createElement('div');
      wrap.className = 'mt-6 text-center';
      btn = document.createElement('button');
      btn.id = 'showcaseLoadMore';
      btn.type = 'button';
      btn.className = 'btn btn-outline w-full sm:w-auto';
      btn.textContent = 'Показать ещё';
      btn.onclick = () => this.renderNextBatch();
      wrap.appendChild(btn);
      grid.insertAdjacentElement('afterend', wrap);

      // Infinite scroll sentinel
      const sentinel = document.createElement('div');
      sentinel.id = 'showcaseSentinel';
      sentinel.style.cssText = 'height:1px;width:100%;margin:0';
      wrap.insertAdjacentElement('afterend', sentinel);

      this.sentinelObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && this.renderedCount < this.filteredData.length) {
          this.renderNextBatch();
        }
      }, { rootMargin: '800px 0px' });

      this.sentinelObserver.observe(sentinel);
    }

    this.loadMoreBtn = btn;
    btn.style.display = this.renderedCount < this.filteredData.length ? '' : 'none';
  }

  initializeSliders() {
    const cards = document.querySelectorAll('.showcase-card:not([data-initialized])');

    cards.forEach(card => {
      const id = card.dataset.id;
      if (this.sliders.has(id)) return;

      card.dataset.initialized = 'true';

      const slider = card.querySelector('.showcase-slider-track');
      const prevBtn = card.querySelector('.showcase-nav-prev');
      const nextBtn = card.querySelector('.showcase-nav-next');
      const dots = card.querySelectorAll('.showcase-dot');
      const images = card.querySelectorAll('.showcase-slider-image');

      if (!slider || !images.length) return;

      if (this.disableAnimations) {
        slider.style.transition = 'none';
      }

      // Error handling for images
      images.forEach(img => {
        img.onerror = () => {
          if (img.dataset.full) {
            img.src = img.dataset.full;
            delete img.dataset.full;
          } else {
            img.src = IMG_PLACEHOLDER;
          }
        };
      });

      const state = {
        currentIndex: 0,
        totalImages: images.length,
        slider,
        dots,
        card
      };

      this.sliders.set(id, state);
      this.ensureImageLoaded(state, 0);

      if (this.playObserver) {
        this.playObserver.observe(card);
      }

      // Event listeners with passive flag for better scroll performance
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

      dots.forEach((dot, index) => {
        dot.onclick = (e) => {
          e.stopPropagation();
          this.stopAutoPlay(id);
          this.goToSlide(id, index);
          this.startAutoPlay(id);
        };
      });

      card.addEventListener('mouseenter', () => this.stopAutoPlay(id), { passive: true });
      card.addEventListener('mouseleave', () => this.startAutoPlay(id), { passive: true });

      // Touch support
      let touchStartX = 0;
      slider.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        this.stopAutoPlay(id);
      }, { passive: true });

      slider.addEventListener('touchend', (e) => {
        const diff = touchStartX - e.changedTouches[0].screenX;
        if (Math.abs(diff) > 50) {
          diff > 0 ? this.goToNext(id) : this.goToPrevious(id);
        }
        this.startAutoPlay(id);
      }, { passive: true });
    });
  }

  goToSlide(id, index) {
    const state = this.sliders.get(id);
    if (!state) return;

    this.ensureImageLoaded(state, index);
    state.currentIndex = index;
    state.slider.style.transform = `translateX(${-index * 100}%)`;
    state.dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
  }

  goToNext(id) {
    const state = this.sliders.get(id);
    if (state) {
      this.goToSlide(id, (state.currentIndex + 1) % state.totalImages);
    }
  }

  goToPrevious(id) {
    const state = this.sliders.get(id);
    if (state) {
      this.goToSlide(id, (state.currentIndex - 1 + state.totalImages) % state.totalImages);
    }
  }

  startAutoPlay(id) {
    if (this.disableAnimations) return;
    this.stopAutoPlay(id);
    this.autoPlayIntervals.set(id, setInterval(() => this.goToNext(id), this.autoPlayDelay));
  }

  stopAutoPlay(id) {
    const interval = this.autoPlayIntervals.get(id);
    if (interval) {
      clearInterval(interval);
      this.autoPlayIntervals.delete(id);
    }
  }

  setupFilters() {
    const buttons = document.querySelectorAll('.js-showcase-filter');
    const scat = new URLSearchParams(location.search).get('scat') || 'all';

    buttons.forEach(btn => {
      const cat = btn.dataset.category || 'all';
      btn.classList.toggle('bg-primary/15', cat === scat);
      btn.classList.toggle('text-primary', cat === scat);
      btn.classList.toggle('border-primary/30', cat === scat);
    });
  }

  setupPromptInsertion() {
    document.addEventListener('click', (e) => {
      const promptEl = e.target.closest('.showcase-prompt');
      if (promptEl) {
        promptEl.classList.toggle('expanded');
        e.stopPropagation();
        return;
      }

      const btn = e.target.closest('.showcase-use-btn');
      if (!btn) return;

      const prompt = btn.dataset.prompt;
      const field = document.getElementById('prompt');

      if (field && prompt) {
        field.value = prompt;
        field.focus();
        field.closest('form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

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
    this.autoPlayIntervals.forEach(clearInterval);
    this.autoPlayIntervals.clear();
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

function initShowcaseGallery(data) {
  showcaseData = (data?.length > 0) ? data : fallbackShowcaseData;
  console.log('Showcase initialized:', showcaseData.length, 'items');
  new ShowcaseGallery(showcaseData);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initShowcaseGallery(window.showcaseGalleryData));
} else {
  initShowcaseGallery(window.showcaseGalleryData);
}

window.initShowcaseGallery = initShowcaseGallery;
