/**
 * Global Video Viewer Modal
 * - Provides window.VideoViewer.open(url, { filename, poster })
 * - Delegated listener for [data-open-video], .js-open-video (from cards), and anchors with data-video-url
 * - Tailwind + CSS vars friendly, dark/light support via base.css variables
 */
(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  const modal = () => qs('#videoViewerModal');
  const bodyWrap = () => qs('#videoViewerBody');
  const dlLink = () => qs('#videoViewerModal [data-mg-download]');

  function safeBasename(url) {
    try {
      if (!url) return 'video.mp4';
      // Handle blob, data, or remote URLs
      if (/^blob:/.test(url)) return 'video.mp4';
      if (/^data:/.test(url)) return 'video.mp4';
      const u = new URL(url, window.location.origin);
      const path = u.pathname || '';
      const last = path.split('/').filter(Boolean).pop() || 'video.mp4';
      return last.endsWith('.mp4') ? last : (last + '.mp4');
    } catch (_) {
      return 'video.mp4';
    }
  }

  function close() {
    const m = modal();
    if (!m) return;
    // Clear video to stop playback and free memory
    try {
      const wrap = bodyWrap();
      if (wrap) wrap.innerHTML = '';
    } catch (_) {}
    m.classList.add('hidden');
    document.body.style.overflow = '';
  }

  function open(url, opts) {
    const m = modal();
    if (!m || !url) return;
    const wrap = bodyWrap();
    if (!wrap) return;

    // Inject video element
    const poster = (opts && opts.poster) ? String(opts.poster) : '';
    wrap.innerHTML = `
      <video class="w-full h-full max-h-[70vh] bg-black" ${poster ? `poster="${poster}"` : ''} controls playsinline>
        <source src="${url}" type="video/mp4">
        Your browser does not support the video tag.
      </video>
    `;

    // Setup download
    const fname = (opts && opts.filename) ? String(opts.filename) : safeBasename(url);
    const a = dlLink();
    if (a) {
      a.setAttribute('href', url);
      a.setAttribute('download', fname);
    }

    // Show modal
    m.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  // Wire close events (delegated)
  document.addEventListener('click', function (e) {
    const closeBtn = e.target.closest('[data-mg-close]');
    if (!closeBtn) return;
    const m = modal();
    if (m && !m.classList.contains('hidden')) {
      e.preventDefault();
      e.stopPropagation();
      close();
    }
  });

  // Close via Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      const m = modal();
      if (m && !m.classList.contains('hidden')) close();
    }
  });

  // Delegated opener
  // Priority:
  // 1) [data-open-video] on any element
  // 2) Anchors/buttons with data-video-url (e.g., from templates)
  // 3) .js-open-video article or child with parent having data-video-url (my_jobs/profile cards)
  document.addEventListener('click', function (e) {
    // Ignore if clicking native video element or play overlay (let existing handlers control playback)
    if (e.target.closest('video') || e.target.closest('.video-play-overlay')) return;

    // Ignore interactive UI controls inside cards so their own handlers work
    // (like, save, open comments, likers list, sound toggle, volume slider, hide switches, follow, etc.)
    if (e.target.closest('.like-toggle, .save-toggle, [data-open-comments], [data-open-likers], .js-like-comment, .hide-toggle, .vid-snd-btn, .vid-vol, [data-follow-toggle]')) {
      return;
    }

    let trigger = e.target.closest('[data-open-video]');
    let url = null;
    let poster = null;
    let filename = null;

    if (!trigger) {
      trigger = e.target.closest('a[data-video-url], button[data-video-url], [data-viewer-video-url]');
    }
    if (trigger) {
      url = trigger.getAttribute('data-video-url') || trigger.getAttribute('data-viewer-video-url') || trigger.getAttribute('href') || '';
      poster = trigger.getAttribute('data-poster') || '';
      filename = trigger.getAttribute('download') || trigger.getAttribute('data-filename') || '';
    }

    // Fallback: support cards with class .js-open-video on parent
    if (!url) {
      const card = e.target.closest('.js-open-video, article.js-open-video');
      if (card) {
        url = card.getAttribute('data-video-url') || '';
        poster = card.getAttribute('data-poster') || poster || '';
        filename = filename || '';
        // A click on play overlay/video should be ignored (handled above).
      }
    }

    // Fallback 2: direct download anchors (gallery/profile) — open viewer instead of navigating
    if (!url) {
      const dlA = e.target.closest('a[download][href], a[href*=".mp4"]');
      if (dlA) {
        const href = dlA.getAttribute('href') || '';
        if (/\.mp4(\?|#|$)/i.test(href)) {
          url = href;
          // Try to infer poster from nearest &lt;video&gt;
          try {
            const scope = dlA.closest('article, .card, .group') || document;
            const vid = scope.querySelector('video');
            if (vid) poster = vid.getAttribute('poster') || poster || '';
          } catch (_) {}
          filename = dlA.getAttribute('download') || filename || '';
        }
      }
    }

    if (!url) return;

    // Open only for plausible video URLs or blobs
    const plausible = /^https?:/.test(url) || /^blob:/.test(url) || /\.mp4(\?|#|$)/i.test(url);
    if (!plausible) return;

    // Prevent default navigation and bubble to avoid competing handlers
    e.preventDefault();
    e.stopPropagation();

    open(url, { filename, poster });
  }, true); // capture to supersede other handlers

  // Export
  window.VideoViewer = { open, close };
})();
