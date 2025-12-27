// Оптимизированный модуль для ускорения страницы генерации
// Использует современные техники: debouncing, throttling, кэширование, делегирование событий

(function() {
  'use strict';

  // Утилиты для оптимизации
  const Utils = {
    // Debounce для частых событий
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    // Throttle для scroll/resize
    throttle(func, limit) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    // Кэш DOM элементов
    cache: new Map(),

    getElement(selector, useCache = true) {
      if (useCache && this.cache.has(selector)) {
        return this.cache.get(selector);
      }
      const el = document.querySelector(selector);
      if (useCache && el) {
        this.cache.set(selector, el);
      }
      return el;
    },

    // Batch DOM updates
    batchUpdate(updates) {
      requestAnimationFrame(() => {
        updates.forEach(update => update());
      });
    },

    // Lazy load images
    lazyLoadImages() {
      if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              const img = entry.target;
              if (img.dataset.src) {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
              }
              observer.unobserve(img);
            }
          });
        }, {
          rootMargin: '50px 0px',
          threshold: 0.01
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
          imageObserver.observe(img);
        });
      }
    },

    // Оптимизированное копирование в буфер
    async copyToClipboard(text) {
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text);
          return true;
        } catch (e) {
          // Clipboard API failed, using fallback
        }
      }

      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;left:-9999px;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      const success = document.execCommand('copy');
      document.body.removeChild(ta);
      return success;
    }
  };

  // Оптимизация модальных окон
  class ModalOptimizer {
    constructor() {
      this.modals = new Map();
      this.init();
    }

    init() {
      // Используем делегирование для всех модальных окон
      document.addEventListener('click', this.handleClick.bind(this), { passive: true });
      document.addEventListener('keydown', this.handleKeydown.bind(this), { passive: true });
    }

    handleClick(e) {
      // Закрытие по клику вне модального окна
      const modal = e.target.closest('.fixed.inset-0');
      if (modal && e.target === modal) {
        this.close(modal);
      }
    }

    handleKeydown(e) {
      if (e.key === 'Escape') {
        const activeModal = document.querySelector('.fixed.inset-0.active, .fixed.inset-0:not(.hidden)');
        if (activeModal) {
          this.close(activeModal);
        }
      }
    }

    close(modal) {
      requestAnimationFrame(() => {
        modal.classList.remove('active');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
      });
    }
  }

  // Оптимизация форм
  class FormOptimizer {
    constructor() {
      this.forms = new Map();
      this.init();
    }

    init() {
      // Кэшируем все формы
      document.querySelectorAll('form').forEach(form => {
        const id = form.id || `form-${Math.random().toString(36).substr(2, 9)}`;
        this.forms.set(id, {
          element: form,
          fields: new Map()
        });

        // Кэшируем поля формы
        form.querySelectorAll('input, textarea, select').forEach(field => {
          if (field.id) {
            this.forms.get(id).fields.set(field.id, field);
          }
        });
      });
    }

    getField(formId, fieldId) {
      return this.forms.get(formId)?.fields.get(fieldId);
    }

    // Debounced валидация
    validateField = Utils.debounce((field) => {
      if (field.validity && !field.validity.valid) {
        field.classList.add('invalid');
      } else {
        field.classList.remove('invalid');
      }
    }, 300);
  }

  // Оптимизация скролла
  class ScrollOptimizer {
    constructor() {
      this.scrollHandlers = new Map();
      this.init();
    }

    init() {
      // Throttled scroll handler
      const handleScroll = Utils.throttle(() => {
        this.scrollHandlers.forEach(handler => handler());
      }, 100);

      window.addEventListener('scroll', handleScroll, { passive: true });
    }

    addHandler(id, handler) {
      this.scrollHandlers.set(id, handler);
    }

    removeHandler(id) {
      this.scrollHandlers.delete(id);
    }
  }

  // Оптимизация анимаций
  class AnimationOptimizer {
    constructor() {
      this.animations = new Map();
    }

    // Используем requestAnimationFrame для плавных анимаций
    animate(id, callback, duration = 300) {
      if (this.animations.has(id)) {
        cancelAnimationFrame(this.animations.get(id));
      }

      const start = performance.now();
      const animate = (currentTime) => {
        const elapsed = currentTime - start;
        const progress = Math.min(elapsed / duration, 1);

        callback(progress);

        if (progress < 1) {
          const frameId = requestAnimationFrame(animate);
          this.animations.set(id, frameId);
        } else {
          this.animations.delete(id);
        }
      };

      const frameId = requestAnimationFrame(animate);
      this.animations.set(id, frameId);
    }

    cancel(id) {
      if (this.animations.has(id)) {
        cancelAnimationFrame(this.animations.get(id));
        this.animations.delete(id);
      }
    }
  }

  // Оптимизация событий
  class EventOptimizer {
    constructor() {
      this.delegatedEvents = new Map();
    }

    // Делегирование событий для динамического контента
    delegate(selector, eventType, handler, options = {}) {
      const key = `${selector}-${eventType}`;

      if (!this.delegatedEvents.has(key)) {
        const delegatedHandler = (e) => {
          const target = e.target.closest(selector);
          if (target) {
            handler.call(target, e);
          }
        };

        document.addEventListener(eventType, delegatedHandler, {
          passive: options.passive !== false,
          capture: options.capture || false
        });

        this.delegatedEvents.set(key, delegatedHandler);
      }
    }
  }

  // Инициализация оптимизаторов
  const init = () => {
    window.pageOptimizers = {
      modal: new ModalOptimizer(),
      form: new FormOptimizer(),
      scroll: new ScrollOptimizer(),
      animation: new AnimationOptimizer(),
      event: new EventOptimizer(),
      utils: Utils
    };

    // Lazy load изображений
    Utils.lazyLoadImages();

    // Оптимизация производительности рендеринга
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        // Предзагрузка критических ресурсов в idle time
        const criticalImages = document.querySelectorAll('img[loading="eager"]');
        criticalImages.forEach(img => {
          if (!img.complete) {
            const tempImg = new Image();
            tempImg.src = img.src;
          }
        });
      });
    }
  };

  // Запуск при загрузке DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true, passive: true });
  } else {
    init();
  }
})();
