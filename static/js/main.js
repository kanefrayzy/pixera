/**
 * AI Gallery - Main JavaScript
 * Common utilities and functions
 */

// CSRF Token Utility
function getCSRFToken() {
  const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

// Debounce utility
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

// Mobile detection
const isMobile = () => window.innerWidth < 768;

// Touch device detection
const isTouchDevice = () => 'ontouchstart' in window || navigator.maxTouchPoints > 0;

// Smooth scroll utility
function smoothScrollTo(element, offset = 0) {
  if (!element) return;
  
  const targetPosition = element.offsetTop - offset;
  window.scrollTo({
    top: targetPosition,
    behavior: 'smooth'
  });
}

// Form validation utilities
const FormValidator = {
  email: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
  password: (password) => password.length >= 8,
  required: (value) => value && value.trim().length > 0
};

// Loading state manager
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

// Toast notifications
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
    
    // Animate in
    requestAnimationFrame(() => {
      toast.style.transform = 'translateX(0)';
      toast.style.opacity = '1';
    });
    
    // Auto remove
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

// Image lazy loading
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

    let lastActive = null;

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
      document.documentElement.style.overflow = lock ? 'hidden' : '';
      document.body.style.overflow = lock ? 'hidden' : '';
    }

    function open() {
      lastActive = document.activeElement;
      drawer.removeAttribute('hidden');
      backdrop.removeAttribute('hidden');
      requestAnimationFrame(() => {
        drawer.style.transform = 'translateX(0)';
        backdrop.style.opacity = '1';
        backdrop.style.pointerEvents = 'auto';
        headerBtn?.setAttribute('aria-expanded', 'true');
        lockScroll(true);
        const firstFocusable = drawer.querySelector('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) firstFocusable.focus(); else drawer.focus();
      });
      drawer.addEventListener('keydown', trapFocus);
    }

    function close() {
      drawer.style.transform = 'translateX(100%)';
      backdrop.style.opacity = '0';
      backdrop.style.pointerEvents = 'none';
      headerBtn?.setAttribute('aria-expanded', 'false');
      const onTransitionEnd = () => {
        drawer.setAttribute('hidden', '');
        backdrop.setAttribute('hidden', '');
        lockScroll(false);
        drawer.removeEventListener('keydown', trapFocus);
        if (lastActive && document.body.contains(lastActive)) lastActive.focus();
      };
      setTimeout(onTransitionEnd, 300);
      drawer.addEventListener('transitionend', onTransitionEnd, { once: true });
    }

    function toggle() { if (drawer.hasAttribute('hidden')) open(); else close(); }

    window.dashboardDrawer = { open, close, toggle };
    closeBtn?.addEventListener('click', close);
    backdrop?.addEventListener('click', close);
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !drawer.hasAttribute('hidden')) close(); });
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-open-dashboard="1"]');
      if (!trigger) return;
      if (trigger.tagName === 'A') e.preventDefault();
      toggle();
    });
    function handleResize(){ if (window.innerWidth >= 768 && !drawer.hasAttribute('hidden')) close(); }
    window.addEventListener('resize', handleResize);
    let startX=0,startY=0,currentX=0,currentY=0,isDragging=false,isSwiping=false;
    drawer.addEventListener('touchstart',(e)=>{ 
      const t=e.touches[0];
      startX=t.clientX; startY=t.clientY; currentX=startX; currentY=startY; 
      isDragging=true; isSwiping=false; 
    },{passive:true});
    drawer.addEventListener('touchmove',(e)=>{
      if(!isDragging) return; 
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
      if(dx>0){ const p=Math.min(dx/drawer.offsetWidth,1); drawer.style.transform=`translateX(${p*100}%)`; backdrop.style.opacity=1-p; }
    },{passive:true});
    drawer.addEventListener('touchend',()=>{ 
      if(!isDragging) return; 
      const dx=currentX-startX; 
      isDragging=false; 
      const th=drawer.offsetWidth*0.3; 
      if(isSwiping && dx>th){ close(); } else { drawer.style.transform='translateX(0)'; backdrop.style.opacity='1'; }
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

// Export utilities for use in other scripts
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