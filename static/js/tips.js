(function(){
  // Scope to this page only
  const root = document.getElementById('tips-root');
  if (!root) return;

  // Copy functionality
  function copyText(selector) {
    const el = document.querySelector(selector);
    if (!el) return false;

    const text = el.textContent || el.value || '';
    if (!text.trim()) return false;

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
      return true;
    }

    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }

  // Copy button handlers
  root.querySelectorAll('.copy-btn[data-target]').forEach(btn => {
    btn.addEventListener('click', () => {
      const success = copyText(btn.dataset.target);
      if (success) {
        const originalText = btn.innerHTML;
        btn.innerHTML = `
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Скопировано
        `;
        btn.classList.add('text-green-600');

        setTimeout(() => {
          btn.innerHTML = originalText;
          btn.classList.remove('text-green-600');
        }, 2000);
      }
    });
  });

  // Prompt builder
  const S = id => document.getElementById(id);
  const out = S('b-out');

  S('b-make')?.addEventListener('click', () => {
    const parts = [
      (S('b-subject')?.value || '').trim(),
      (S('b-light')?.value || '').trim(),
      (S('b-lens')?.value || '').trim(),
      (S('b-mat')?.value || '').trim(),
      (S('b-mood')?.value || '').trim()
    ].filter(Boolean);

    if (parts.length === 0) {
      out.textContent = 'Заполните хотя бы одно поле выше';
      return;
    }

    out.textContent = parts.join(', ');
    out.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  // Tag buttons - add to mood field
  root.querySelectorAll('.tag-btn[data-tag]').forEach(tag => {
    tag.addEventListener('click', () => {
      const inp = S('b-mood');
      if (!inp) return;

      const tagValue = tag.dataset.tag || '';
      const currentValue = inp.value.trim();

      if (currentValue) {
        inp.value = currentValue + ', ' + tagValue;
      } else {
        inp.value = tagValue;
      }

      inp.focus();

      // Visual feedback
      tag.classList.add('bg-primary/20', 'border-primary', 'text-primary');
      setTimeout(() => {
        tag.classList.remove('bg-primary/20', 'border-primary', 'text-primary');
      }, 500);
    });
  });

  // Auto-build on input change with debounce
  const inputIds = ['b-subject', 'b-light', 'b-lens', 'b-mat', 'b-mood'];
  inputIds.forEach(id => {
    const input = S(id);
    if (input) {
      input.addEventListener('input', () => {
        clearTimeout(input.buildTimeout);
        input.buildTimeout = setTimeout(() => {
          const hasContent = inputIds.some(inputId => S(inputId)?.value?.trim());
          if (hasContent) S('b-make')?.click();
        }, 800);
      });
    }
  });

  // Enhanced details animations
  root.querySelectorAll('details').forEach(details => {
    details.addEventListener('toggle', () => {
      if (details.open) {
        const content = details.querySelector('div');
        if (content) {
          content.style.opacity = '0';
          content.style.transform = 'translateY(-10px)';
          requestAnimationFrame(() => {
            content.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
            content.style.opacity = '1';
            content.style.transform = 'translateY(0)';
          });
        }
      }
    });
  });
})();
