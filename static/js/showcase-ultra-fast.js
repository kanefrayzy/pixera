/**
 * Ultra-Fast Showcase Loader
 * Optimized for maximum speed with compressed images/videos and dynamic loading
 */

(function() {
  'use strict';

  const CONFIG = {
    THUMB_QUALITY: 0.6,
    THUMB_MAX_WIDTH: 400,
    THUMB_MAX_HEIGHT: 400,
    VIDEO_PREVIEW_DURATION: 3,
    LAZY_LOAD_THRESHOLD: '50px',
    ITEMS_PER_BATCH: 8,
    CACHE_DURATION: 3600000, // 1 hour
    PRELOAD_COUNT: 4
  };

  class ShowcaseOptimizer {
    constructor() {
      this.grid = document.getElementById('showcaseGrid');
      this.filters = document.querySelectorAll('.js-showcase-filter');
      this.currentCategory = 'all';
      this.allItems = [];
      this.displayedCount = 0;
      this.observer = null;
      this.cache = new Map();
      this.loadingMore = false;

      this.init();
    }

    init() {
      if (!this.grid) return;

      this.loadCachedData();
      this.setupFilters();
      this.setupIntersectionObserver();
      this.loadInitialBatch();
      this.setupLoadMoreTrigger();
    }

    loadCachedData() {
      try {
        const cached = localStorage.getItem('showcase_cache');
        const timestamp = localStorage.getItem('showcase_cache_time');

        if (cached && timestamp) {
          const age = Date.now() - parseInt(timestamp);
          if (age < CONFIG.CACHE_DURATION) {
            this.allItems = JSON.parse(cached);
            console.log('Loaded', this.allItems.length, 'items from cache');
            return;
          }
        }
      } catch (e) {
        console.warn('Cache load failed:', e);
      }

      // Fallback to window data
      this.allItems = window.showcaseGalleryData || [];
      this.cacheData();
    }

    cacheData() {
      try {
        localStorage.setItem('showcase_cache', JSON.stringify(this.allItems));
        localStorage.setItem('showcase_cache_time', Date.now().toString());
      } catch (e) {
        console.warn('Cache save failed:', e);
      }
    }

    setupFilters() {
      this.filters.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const category = btn.dataset.category;

          if (category === this.currentCategory) return;

          this.filters.forEach(b => {
            b.classList.remove('bg-primary/15', 'text-primary', 'border-primary/30');
          });
          btn.classList.add('bg-primary/15', 'text-primary', 'border-primary/30');

          this.currentCategory = category;
          this.displayedCount = 0;
          this.grid.innerHTML = '';
          this.loadInitialBatch();
        });
      });
    }

    setupIntersectionObserver() {
      const options = {
        root: null,
        rootMargin: CONFIG.LAZY_LOAD_THRESHOLD,
        threshold: 0.01
      };

      this.observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            this.loadImage(entry.target);
          }
        });
      }, options);
    }

    setupLoadMoreTrigger() {
      const sentinel = document.createElement('div');
      sentinel.className = 'load-more-sentinel';
      sentinel.style.cssText = 'height:1px;width:100%;';

      const sentinelObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !this.loadingMore) {
          this.loadMoreItems();
        }
      }, { rootMargin: '200px' });

      this.grid.parentElement.appendChild(sentinel);
      sentinelObserver.observe(sentinel);
    }

    getFilteredItems() {
      if (this.currentCategory === 'all') {
        return this.allItems;
      }
      return this.allItems.filter(item => item.category === this.currentCategory);
    }

    loadInitialBatch() {
      const items = this.getFilteredItems();
      const batch = items.slice(0, CONFIG.ITEMS_PER_BATCH);

      if (batch.length === 0) {
        this.grid.innerHTML = '<div class="col-span-full text-center text-[var(--muted)] py-8">Примеры не найдены</div>';
        return;
      }

      batch.forEach(item => this.createCard(item));
      this.displayedCount = batch.length;

      // Preload next batch
      this.preloadNextBatch();
    }

    loadMoreItems() {
      if (this.loadingMore) return;

      const items = this.getFilteredItems();
      const remaining = items.length - this.displayedCount;

      if (remaining <= 0) return;

      this.loadingMore = true;
      const batch = items.slice(this.displayedCount, this.displayedCount + CONFIG.ITEMS_PER_BATCH);

      requestAnimationFrame(() => {
        batch.forEach(item => this.createCard(item));
        this.displayedCount += batch.length;
        this.loadingMore = false;

        // Preload next batch
        this.preloadNextBatch();
      });
    }

    preloadNextBatch() {
      const items = this.getFilteredItems();
      const nextBatch = items.slice(
        this.displayedCount,
        this.displayedCount + CONFIG.PRELOAD_COUNT
      );

      nextBatch.forEach(item => {
        if (item.images && item.images[0]) {
          const img = new Image();
          img.src = item.images[0].thumb;
        }
      });
    }

    createCard(item) {
      const card = document.createElement('div');
      card.className = 'showcase-card group relative rounded-xl overflow-hidden bg-[var(--card)] border border-[var(--bord)] hover:border-primary/50 transition-all duration-300 cursor-pointer';
      card.dataset.category = item.category;

      const aspectRatio = 'aspect-[3/4]';

      card.innerHTML = `
        <div class="${aspectRatio} relative overflow-hidden bg-[var(--bord)]">
          <div class="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900 animate-pulse"></div>
          <img
            data-src="${this.escapeHtml(item.images[0]?.thumb || '')}"
            data-full="${this.escapeHtml(item.images[0]?.full || '')}"
            alt="${this.escapeHtml(item.title)}"
            class="lazy-img absolute inset-0 w-full h-full object-cover opacity-0 transition-opacity duration-300"
            loading="lazy"
            decoding="async"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div class="absolute bottom-0 left-0 right-0 p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
            <h3 class="text-white font-semibold text-sm mb-1 line-clamp-1">${this.escapeHtml(item.title)}</h3>
            ${item.prompt ? `<p class="text-white/80 text-xs line-clamp-2">${this.escapeHtml(item.prompt)}</p>` : ''}
          </div>
        </div>
      `;

      const img = card.querySelector('.lazy-img');
      this.observer.observe(img);

      card.addEventListener('click', () => this.openLightbox(item));

      this.grid.appendChild(card);
    }

    loadImage(img) {
      if (img.src || !img.dataset.src) return;

      const thumb = img.dataset.src;

      // Create a temporary image to load
      const tempImg = new Image();
      tempImg.onload = () => {
        img.src = thumb;
        img.classList.add('opacity-100');
        img.classList.remove('opacity-0');

        // Remove placeholder
        const placeholder = img.previousElementSibling;
        if (placeholder && placeholder.classList.contains('animate-pulse')) {
          placeholder.remove();
        }
      };

      tempImg.onerror = () => {
        console.warn('Failed to load:', thumb);
        img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23ddd" width="400" height="400"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3EНе загружено%3C/text%3E%3C/svg%3E';
        img.classList.add('opacity-100');
      };

      tempImg.src = thumb;
      this.observer.unobserve(img);
    }

    openLightbox(item) {
      // Create lightbox modal
      const modal = document.createElement('div');
      modal.className = 'fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4';
      modal.innerHTML = `
        <button class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors" aria-label="Закрыть">
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
        <div class="max-w-4xl w-full">
          <img src="${this.escapeHtml(item.images[0]?.full || item.images[0]?.thumb || '')}"
               alt="${this.escapeHtml(item.title)}"
               class="w-full h-auto rounded-lg shadow-2xl"
               loading="eager">
          <div class="mt-4 text-white">
            <h3 class="text-xl font-bold mb-2">${this.escapeHtml(item.title)}</h3>
            ${item.prompt ? `<p class="text-white/80 text-sm">${this.escapeHtml(item.prompt)}</p>` : ''}
          </div>
        </div>
      `;

      const closeBtn = modal.querySelector('button');
      closeBtn.addEventListener('click', () => {
        modal.remove();
        document.body.style.overflow = '';
      });

      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.remove();
          document.body.style.overflow = '';
        }
      });

      document.body.appendChild(modal);
      document.body.style.overflow = 'hidden';
    }

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text || '';
      return div.innerHTML;
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ShowcaseOptimizer());
  } else {
    new ShowcaseOptimizer();
  }
})();
