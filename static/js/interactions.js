// Like functionality
const LikeManager = {
  init: () => {
    document.addEventListener('click', LikeManager.handleLike);
  },

  handleLike: async (e) => {
    const btn = e.target.closest('.like-toggle');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    if (btn.disabled || btn.dataset.loading === '1') return;

    btn.dataset.loading = '1';
    btn.disabled = true;

    const url = btn.dataset.url;
    const countId = btn.dataset.countTarget || btn.dataset.id;
    const countEl = countId ? document.getElementById(countId) || document.getElementById(`like-count-${countId}`) : null;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': window.AIGallery.getCSRFToken(),
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
      });

      const data = await response.json().catch(() => null);
      if (!response.ok || !data || data.ok !== true) {
        throw new Error('Like request failed');
      }

      // Update button state
      const heart = btn.querySelector('svg');
      const isLiked = !!data.liked;

      btn.setAttribute('aria-pressed', isLiked ? 'true' : 'false');

      if (isLiked) {
        btn.classList.add('text-red-500');
        btn.classList.remove('text-[var(--muted)]');
        if (heart) heart.setAttribute('fill', 'currentColor');
      } else {
        btn.classList.remove('text-red-500');
        btn.classList.add('text-[var(--muted)]');
        if (heart) heart.setAttribute('fill', 'none');
      }

      // Update count
      if (countEl && typeof data.count === 'number') {
        countEl.textContent = data.count;
      }

      // Animate button
      btn.style.transform = 'scale(1.1)';
      setTimeout(() => {
        btn.style.transform = 'scale(1)';
      }, 150);

    } catch (err) {
      console.warn('Like failed:', err);
      window.AIGallery.Toast.show('Не удалось поставить лайк', 'error');
    } finally {
      delete btn.dataset.loading;
      btn.disabled = false;
    }
  }
};

// Comment like functionality
const CommentLikeManager = {
  init: () => {
    document.addEventListener('click', CommentLikeManager.handleLike);
  },

  handleLike: async (e) => {
    const btn = e.target.closest('.js-like-comment');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    if (btn.disabled || btn.dataset.loading === '1') return;

    btn.dataset.loading = '1';
    btn.disabled = true;

    try {
      const response = await fetch(btn.dataset.url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': window.AIGallery.getCSRFToken(),
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
      });

      const data = await response.json().catch(() => null);
      if (!response.ok || !data || data.ok !== true) {
        throw new Error('Comment like failed');
      }

      // Update like count
      const countId = btn.dataset.countId;
      const countEl = countId && document.getElementById(countId);
      if (countEl && typeof data.count === 'number') {
        countEl.textContent = data.count;
      }

      // Update button state
      const heart = btn.querySelector('svg');
      const isLiked = !!data.liked;

      btn.setAttribute('aria-pressed', isLiked ? 'true' : 'false');

      if (isLiked) {
        btn.classList.add('text-red-500');
        btn.classList.remove('text-[var(--muted)]');
        if (heart) heart.setAttribute('fill', 'currentColor');
      } else {
        btn.classList.remove('text-red-500');
        btn.classList.add('text-[var(--muted)]');
        if (heart) heart.setAttribute('fill', 'none');
      }

    } catch (err) {
      console.warn('Comment like failed:', err);
      window.AIGallery.Toast.show('Не удалось поставить лайк', 'error');
    } finally {
      delete btn.dataset.loading;
      btn.disabled = false;
    }
  }
};

// Reply toggle functionality
const ReplyManager = {
  init: () => {
    document.addEventListener('click', ReplyManager.handleToggle);
  },

  handleToggle: (e) => {
    const toggleBtn = e.target.closest('.js-reply-toggle');
    if (!toggleBtn) return;

    const targetId = toggleBtn.getAttribute('data-target');
    const form = document.getElementById(targetId);

    if (form) {
      const isHidden = form.classList.contains('hidden');
      form.classList.toggle('hidden', !isHidden);

      // Focus on textarea when showing
      if (isHidden) {
        const textarea = form.querySelector('textarea');
        if (textarea) {
          setTimeout(() => textarea.focus(), 100);
        }
      }

      // Update button text
      toggleBtn.textContent = isHidden ? 'Скрыть' : 'Ответить';
    }
  }
};

// Comment form handler
const CommentManager = {
  init: () => {
    document.querySelectorAll('form[data-comment-form]').forEach(form => {
      form.addEventListener('submit', CommentManager.handleSubmit);
    });
  },

  handleSubmit: async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const textarea = form.querySelector('textarea');

    if (!textarea.value.trim()) {
      window.AIGallery.Toast.show('Напишите комментарий', 'warning');
      textarea.focus();
      return;
    }

    window.AIGallery.LoadingManager.show(submitBtn, 'Отправка...');

    try {
      const formData = new FormData(form);
      const response = await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': window.AIGallery.getCSRFToken(),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (response.ok) {
        // Reload page to show new comment
        window.location.reload();
      } else {
        throw new Error('Comment submission failed');
      }
    } catch (error) {
      console.error('Comment submission error:', error);
      window.AIGallery.Toast.show('Не удалось отправить комментарий', 'error');
    } finally {
      window.AIGallery.LoadingManager.hide(submitBtn);
    }
  }
};

// Image gallery functionality
const GalleryManager = {
  init: () => {
    // Add loading placeholders
    document.querySelectorAll('.gallery-item img').forEach(img => {
      img.addEventListener('load', () => {
        img.classList.add('loaded');
      });

      img.addEventListener('error', () => {
        img.classList.add('error');
        img.alt = 'Изображение не загрузилось';
      });
    });

    // Add hover effects for non-touch devices
    if (!window.AIGallery.isTouchDevice()) {
      document.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('mouseenter', () => {
          item.style.transform = 'translateY(-4px)';
        });

        item.addEventListener('mouseleave', () => {
          item.style.transform = 'translateY(0)';
        });
      });
    }
  }
};

// Auto-slug functionality for forms
const SlugManager = {
  init: () => {
    document.querySelectorAll('[data-slug-source]').forEach(input => {
      const sourceSelector = input.dataset.slugSource;
      const sourceInput = document.querySelector(sourceSelector);

      if (sourceInput) {
        sourceInput.addEventListener('input', window.AIGallery.debounce(() => {
          if (!input.dataset.touched) {
            input.value = SlugManager.slugify(sourceInput.value);
          }
        }, 300));

        input.addEventListener('input', () => {
          input.dataset.touched = '1';
        });
      }
    });
  },

  slugify: (str) => {
    return str
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
      .replace(/[^a-z0-9\-_\s]+/g, '') // Remove special chars
      .trim()
      .replace(/\s+/g, '-') // Replace spaces with dashes
      .slice(0, 80); // Limit length
  }
};

// Initialize all interaction managers
document.addEventListener('DOMContentLoaded', () => {
  LikeManager.init();
  CommentLikeManager.init();
  ReplyManager.init();
  CommentManager.init();
  GalleryManager.init();
  SlugManager.init();
});

// Export for external use
window.AIGallery.Interactions = {
  LikeManager,
  CommentLikeManager,
  ReplyManager,
  CommentManager,
  GalleryManager,
  SlugManager
};
