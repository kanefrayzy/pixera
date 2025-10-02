function getCSRFToken() {
  const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const isMobile = () => window.innerWidth < 768;
const isTouchDevice = () => 'ontouchstart' in window || navigator.maxTouchPoints > 0;

function smoothScrollTo(element, offset = 0) {
  if (!element) return;
  const targetPosition = element.offsetTop - offset;
  window.scrollTo({ top: targetPosition, behavior: 'smooth' });
}

const FormValidator = {
  email: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
  password: (password) => password.length >= 8,
  required: (value) => value && value.trim().length > 0
};

const LoadingManager = {
  show: (element, text = 'Загрузка...') => {
    if (!element) return;
    element.disabled = true;
    element.dataset.originalText = element.textContent;
    element.textContent = text;
    element.classList.add('opacity-70');
  },
  hide: (element) => {
    if (!element) return;
    element.disabled = false;
    if (element.dataset.originalText) {
      element.textContent = element.dataset.originalText;
      delete element.dataset.originalText;
    }
    element.classList.remove('opacity-70');
  }
};

const Toast = {
  show: (message, type = 'info', duration = 3000) => {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-50 p-4 rounded-xl border backdrop-blur-sm transition-all duration-300 max-w-sm ${
      type === 'success' ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200' :
      type === 'error' ? 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200' :
      type === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-200' :
      'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-200'
    }`;

    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.style.transform = 'translateX(0)';
      toast.style.opacity = '1';
    });

    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      toast.style.opacity = '0';
      setTimeout(() => {
        if (toast.parentNode) {
          document.body.removeChild(toast);
        }
      }, 300);
    }, duration);
  }
};

const LazyLoader = {
  init: () => {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            observer.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    } else {
      // Fallback for older browsers
      document.querySelectorAll('img[data-src]').forEach(img => {
        img.src = img.dataset.src;
      });
    }
  }
};

// Responsive image handler
const ResponsiveImages = {
  updateSizes: () => {
    const images = document.querySelectorAll('img[data-sizes]');
    images.forEach(img => {
      const sizes = JSON.parse(img.dataset.sizes || '{}');
      const screenWidth = window.innerWidth;

      let appropriateSize = sizes.default || img.src;

      if (screenWidth <= 480 && sizes.mobile) {
        appropriateSize = sizes.mobile;
      } else if (screenWidth <= 768 && sizes.tablet) {
        appropriateSize = sizes.tablet;
      } else if (sizes.desktop) {
        appropriateSize = sizes.desktop;
      }

      if (img.src !== appropriateSize) {
        img.src = appropriateSize;
      }
    });
  }
};

// Modal manager
const Modal = {
  open: (modalId) => {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Focus trap
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }
  },

  close: (modalId) => {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
};

// Initialize common functionality
document.addEventListener('DOMContentLoaded', () => {
  // Initialize lazy loading
  LazyLoader.init();

  // Handle responsive images
  ResponsiveImages.updateSizes();
  window.addEventListener('resize', debounce(ResponsiveImages.updateSizes, 250));

  // Close modals on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
        Modal.close(modal.id);
      });
    }
  });

  // Close modals on backdrop click
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
      const modal = e.target.closest('.modal');
      if (modal) {
        Modal.close(modal.id);
      }
    }
  });

  // Dashboard Drawer init (migrated from template)
  (function initDashboardDrawer(){
    const drawer = document.getElementById('dashboardDrawer');
    const backdrop = document.getElementById('dbBackdrop');
    const closeBtn = document.getElementById('dbDrawerClose');
    const headerBtn = document.getElementById('cabinetBtn');

    if (!drawer || !backdrop) return;

    let isAnimating = false;
    let isOpen = false;
    let lastActive = null;
    let animationTimeout = null;

    function trapFocus(e) {
      if (e.key !== 'Tab') return;
      const focusables = drawer.querySelectorAll('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }

    function lockScroll(lock) {
      if (window.innerWidth >= 768) {
        return;
      }

      if (lock) {
        const scrollY = window.scrollY;
        document.body.style.position = 'fixed';
        document.body.style.top = `-${scrollY}px`;
        document.body.style.width = '100%';
        document.body.style.overflow = 'hidden';
      } else {
        const scrollY = document.body.style.top;
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        document.body.style.overflow = '';

        if (scrollY) {
          window.scrollTo(0, parseInt(scrollY || '0', 10) * -1);
        }
      }
    }    function checkIsOpen() {
      return isOpen && !drawer.hasAttribute('hidden');
    }

    function open() {
      if (isAnimating || isOpen) {
        console.log('Drawer: already opening or open');
        return;
      }

      console.log('Drawer: starting open');
      isAnimating = true;
      isOpen = true;

      if (animationTimeout) {
        clearTimeout(animationTimeout);
      }

      lastActive = document.activeElement;
      drawer.removeAttribute('hidden');
      backdrop.removeAttribute('hidden');

      drawer.style.transform = 'translateX(100%)';
      backdrop.style.opacity = '0';
      backdrop.style.pointerEvents = 'none';

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          drawer.style.transform = 'translateX(0)';
          backdrop.style.opacity = '1';
          backdrop.style.pointerEvents = 'auto';
          headerBtn?.setAttribute('aria-expanded', 'true');

          if (window.innerWidth < 768) {
            lockScroll(true);
          }

          animationTimeout = setTimeout(() => {
            isAnimating = false;
            console.log('Drawer: open complete');
            const firstFocusable = drawer.querySelector('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) firstFocusable.focus(); else drawer.focus();
          }, 350);
        });
      });

      drawer.addEventListener('keydown', trapFocus);
    }    function close() {
      if (isAnimating || !isOpen) {
        console.log('Drawer: already closing or closed');
        return;
      }

      console.log('Drawer: starting close');
      isAnimating = true;
      isOpen = false;

      if (animationTimeout) {
        clearTimeout(animationTimeout);
      }

      drawer.style.transform = 'translateX(100%)';
      backdrop.style.opacity = '0';
      backdrop.style.pointerEvents = 'none';
      headerBtn?.setAttribute('aria-expanded', 'false');

      animationTimeout = setTimeout(() => {
        drawer.setAttribute('hidden', '');
        backdrop.setAttribute('hidden', '');

        if (window.innerWidth < 768) {
          lockScroll(false);
        }

        drawer.removeEventListener('keydown', trapFocus);
        isAnimating = false;
        console.log('Drawer: close complete');

        if (lastActive && document.body.contains(lastActive)) {
          try {
            lastActive.focus();
          } catch(e) {
            console.warn('Could not restore focus:', e);
          }
        }
      }, 350);
    }    function toggle() {
      if (isAnimating) {
        console.log('Drawer: animation in progress, ignoring toggle');
        return;
      }
      console.log('Drawer: toggle called, current state:', isOpen ? 'open' : 'closed');
      isOpen ? close() : open();
    }

    // Экспортируем API
    window.dashboardDrawer = {
      open,
      close,
      toggle,
      isOpen: checkIsOpen,
      // Для отладки
      _debug: () => ({ isAnimating, isOpen, hidden: drawer.hasAttribute('hidden') })
    };

    // Обработчики событий с дебаунсом
    let clickTimeout = null;

    closeBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (clickTimeout) return;
      clickTimeout = setTimeout(() => { clickTimeout = null; }, 300);
      close();
    });

    backdrop?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (clickTimeout) return;
      clickTimeout = setTimeout(() => { clickTimeout = null; }, 300);
      close();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        close();
      }
    });

    // Обработчик для мобильных кнопок с data-open-dashboard
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-open-dashboard="1"]');
      if (!trigger) return;
      e.preventDefault();
      e.stopPropagation();
      if (clickTimeout) return;
      clickTimeout = setTimeout(() => { clickTimeout = null; }, 300);
      toggle();
    });

    function handleResize(){
      if (window.innerWidth >= 768 && checkIsOpen()) {
        lockScroll(false);
        close();
      }
    }
    window.addEventListener('resize', handleResize);

    // Touch события для свайпа
    let startX=0, startY=0, currentX=0, currentY=0, isDragging=false, isSwiping=false;

    drawer.addEventListener('touchstart',(e)=>{
      if (isAnimating) return;
      const t=e.touches[0];
      startX=t.clientX; startY=t.clientY; currentX=startX; currentY=startY;
      isDragging=true; isSwiping=false;
    },{passive:true});

    drawer.addEventListener('touchmove',(e)=>{
      if(!isDragging || isAnimating) return;
      const t=e.touches[0];
      currentX=t.clientX; currentY=t.clientY;
      const dx=currentX-startX; const dy=currentY-startY;
      if(!isSwiping){
        if(Math.abs(dx)>Math.abs(dy) && Math.abs(dx)>10){
          isSwiping=true; // распознаём горизонтальный жест
        } else {
          return; // вертикальный скролл — не мешаем
        }
      }
      if(dx>0){
        const p=Math.min(dx/drawer.offsetWidth,1);
        drawer.style.transform=`translateX(${p*100}%)`;
        backdrop.style.opacity=(1-p).toString();
      }
    },{passive:true});

    drawer.addEventListener('touchend',()=>{
      if(!isDragging) return;
      const dx=currentX-startX;
      isDragging=false;
      const th=drawer.offsetWidth*0.3;
      if(isSwiping && dx>th){
        close();
      } else if (isSwiping) {
        // Возвращаем в исходное положение
        drawer.style.transform='translateX(0)';
        backdrop.style.opacity='1';
      }
      isSwiping=false;
    },{passive:true});
  })();

  // Enhance form submissions
  document.querySelectorAll('form[data-ajax]').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const submitBtn = form.querySelector('button[type="submit"]');
      LoadingManager.show(submitBtn, 'Отправка...');

      try {
        const formData = new FormData(form);
        const response = await fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        const result = await response.json();

        if (result.success) {
          Toast.show(result.message || 'Операция выполнена успешно', 'success');
          if (result.redirect) {
            window.location.href = result.redirect;
          }
        } else {
          Toast.show(result.message || 'Произошла ошибка', 'error');
        }
      } catch (error) {
        console.error('Form submission error:', error);
        Toast.show('Произошла ошибка при отправке формы', 'error');
      } finally {
        LoadingManager.hide(submitBtn);
      }
    });
  });
});

window.AIGallery = {
  getCSRFToken,
  debounce,
  isMobile,
  isTouchDevice,
  smoothScrollTo,
  FormValidator,
  LoadingManager,
  Toast,
  LazyLoader,
  ResponsiveImages,
  Modal
};

// Theme Management
const ThemeManager = {
  init() {
    this.themeToggle = document.getElementById('themeToggle');
    this.themeToggleM = document.getElementById('themeToggleMobile');
    this.themeToggleD = document.getElementById('themeToggleDrawer');
    this.iconSun = document.getElementById('iconSun');
    this.iconMoon = document.getElementById('iconMoon');
    this.iconSunM = document.getElementById('iconSunM');
    this.iconMoonM = document.getElementById('iconMoonM');
    this.iconSunD = document.getElementById('iconSunD');
    this.iconMoonD = document.getElementById('iconMoonD');
    this.meta = document.getElementById('themeColor');

    // Устанавливаем текущую тему
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    this.setTheme(current);

    // Обработчики событий
    this.themeToggle?.addEventListener('click', () => this.toggleTheme());
    this.themeToggleM?.addEventListener('click', () => this.toggleTheme());
    this.themeToggleD?.addEventListener('click', () => this.toggleTheme());
  },

  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch(_) {}

    this.themeToggle?.setAttribute('aria-pressed', String(theme === 'dark'));
    this.themeToggleM?.setAttribute('aria-pressed', String(theme === 'dark'));
    this.themeToggleD?.setAttribute('aria-pressed', String(theme === 'dark'));

    if (this.meta) this.meta.setAttribute('content', theme === 'dark' ? '#0B0E14' : '#F7F8FA');

    // Обновляем иконки
    this.syncIcons(theme);
  },

  syncIcons(theme) {
    if (this.iconSun && this.iconMoon) {
      this.iconSun.classList.toggle('hidden', theme !== 'light');
      this.iconMoon.classList.toggle('hidden', theme !== 'dark');
    }
    if (this.iconSunM && this.iconMoonM) {
      this.iconSunM.classList.toggle('hidden', theme !== 'light');
      this.iconMoonM.classList.toggle('hidden', theme !== 'dark');
    }
    if (this.iconSunD && this.iconMoonD) {
      this.iconSunD.classList.toggle('hidden', theme !== 'light');
      this.iconMoonD.classList.toggle('hidden', theme !== 'dark');
    }
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = current === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }
};

// Mobile Menu Management
const MobileMenuManager = {
  init() {
    this.menuBtn = document.getElementById('menuBtn');
    this.mobileMenu = document.getElementById('mobileMenu');

    if (!this.menuBtn || !this.mobileMenu) return;

    this.menuBtn.addEventListener('click', () => this.toggle());

    // Закрываем меню при клике на ссылки
    this.mobileMenu.addEventListener('click', (e) => {
      if (e.target.tagName === 'A' || e.target.closest('a')) {
        this.close();
      }
    });

    // Обработка изменения размера окна
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 768) {
        this.close();
      }
    });
  },

  toggle() {
    const isHidden = this.mobileMenu.classList.contains('hidden');
    isHidden ? this.open() : this.close();
  },

  open() {
    this.mobileMenu.classList.remove('hidden');
    this.menuBtn.setAttribute('aria-expanded', 'true');
  },

  close() {
    this.mobileMenu.classList.add('hidden');
    this.menuBtn.setAttribute('aria-expanded', 'false');
  }
};

const HeaderScrollEffect = {
  init() {
    this.header = document.getElementById('site-header');
    if (!this.header) return;

    this.shadowClass = 'shadow-[0_4px_20px_rgba(0,0,0,.25)]';
    this.onScroll = () => {
      if (window.scrollY > 6) {
        this.header.classList.add(this.shadowClass);
      } else {
        this.header.classList.remove(this.shadowClass);
      }
    };

    this.onScroll();
    window.addEventListener('scroll', this.onScroll, { passive: true });
  }
};

const DashboardIntegration = {
  init() {
    document.getElementById('cabinetBtn')?.addEventListener('click', (e) => {
      e.preventDefault();
      if (window.dashboardDrawer?.toggle) {
        window.dashboardDrawer.toggle();
      } else {
        setTimeout(() => {
          if (window.dashboardDrawer?.toggle) {
            window.dashboardDrawer.toggle();
          } else {
            window.location.href = e.target.href;
          }
        }, 100);
      }
    });
    this.autoOpenDrawer();
  },

  autoOpenDrawer() {
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.get('drawer') === '1') {
        const checkDrawer = () => {
          if (window.dashboardDrawer?.open) {
            window.dashboardDrawer.open();
            url.searchParams.delete('drawer');
            history.replaceState(null, '', url.pathname + (url.searchParams.toString() ? '?' + url.searchParams.toString() : '') + url.hash);
          } else {
            setTimeout(checkDrawer, 50);
          }
        };
        setTimeout(checkDrawer, 100);
      }
    } catch(e) {}
  }
};

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  MobileMenuManager.init();
  HeaderScrollEffect.init();
  DashboardIntegration.init();
});
