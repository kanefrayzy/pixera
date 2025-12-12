const LanguageSwitcher = {
  supportedLangs: ['en', 'es', 'pt', 'de', 'ru'],
  defaultLang: 'ru',
  prefixDefault: false,

  langFlags: {
    'en': '/static/img/flags/gb.svg',
    'ru': '/static/img/flags/ru.svg',
    'de': '/static/img/flags/de.svg',
    'es': '/static/img/flags/es.svg',
    'pt': '/static/img/flags/pt.svg'
  },

  init() {
    this.initSwitcher('langSwitch', 'langMenu', 'currentLangFlag');
    this.initSwitcher('langSwitchMobile', 'langMenuMobile', 'currentLangFlagM');
    this.initSwitcher('langSwitchDrawer', 'langMenuDrawer', 'currentLangFlagDrawer');

    // Обновляем флаг при загрузке
    const currentLang = this.getCurrentLanguage();
    this.updateFlagIcon(currentLang);
  },

  updateFlagIcon(lang) {
    const flagUrl = this.langFlags[lang] || this.langFlags[this.defaultLang];

    const flags = [
      'currentLangFlag',
      'currentLangFlagM',
      'currentLangFlagDrawer',
      'currentLangFlagDrawerGuest'
    ];

    flags.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.tagName === 'IMG') {
        el.src = flagUrl;
      }
    });
  },

  initSwitcher(switchId, menuId, flagId) {
    const switcher = document.getElementById(switchId);
    const menu = document.getElementById(menuId);

    if (!switcher || !menu) return;

    switcher.addEventListener('toggle', () => {
      const summary = switcher.querySelector('summary');
      if (summary) {
        summary.setAttribute('aria-expanded', switcher.hasAttribute('open') ? 'true' : 'false');
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && switcher.hasAttribute('open')) {
        switcher.removeAttribute('open');
      }
    });

    document.addEventListener('pointerdown', (e) => {
      if (!switcher.contains(e.target)) {
        switcher.removeAttribute('open');
      }
    });

    this.markActiveLanguage(menu, this.getCurrentLanguage());

    menu.addEventListener('click', (e) => {
      const item = e.target.closest('button[data-lang]');
      if (!item) return;

      e.preventDefault();
      const lang = (item.getAttribute('data-lang') || '').toLowerCase();
      this.setLanguage(lang, switcher, menu, flagId);
    });
  },

  getCurrentLanguage() {
    // 1. Проверяем cookie django_language
    const cookieMatch = document.cookie.match(/(?:^|;\s*)django_language=([^;]+)/);
    if (cookieMatch) {
      const cookieLang = cookieMatch[1].toLowerCase();
      if (this.supportedLangs.includes(cookieLang)) return cookieLang;
    }

    // 2. Проверяем URL
    const urlMatch = location.pathname.match(/^\/(en|es|pt|de|ru)(?:\/|$)/);
    if (urlMatch) return urlMatch[1];

    // 3. Проверяем HTML lang атрибут
    const htmlLang = (document.documentElement.getAttribute('lang') || '').toLowerCase();
    if (this.supportedLangs.includes(htmlLang)) return htmlLang;

    // 4. Возвращаем язык по умолчанию
    return this.defaultLang;
  },

  markActiveLanguage(menu, activeLanguage) {
    menu.querySelectorAll('button[data-lang]').forEach(btn => {
      const btnLang = (btn.getAttribute('data-lang') || '').toLowerCase();
      const isActive = btnLang === activeLanguage;

      btn.setAttribute('aria-checked', String(isActive));
      btn.style.fontWeight = isActive ? '600' : '400';
    });
  },

  normalizePath(path) {
    path = path.replace(/^\/(en|es|pt|de|ru)(?=\/|$)/, '');
    if (!path.startsWith('/')) path = '/' + path;
    return path || '/';
  },

  buildLanguageUrl(language) {
    let path = this.normalizePath(location.pathname);

    if (this.prefixDefault || language !== this.defaultLang) {
      path = '/' + language + (path.startsWith('/') ? '' : '/') + path;
    }

    const url = new URL(location.href);
    url.pathname = path;
    url.searchParams.delete('lang');

    return url.toString();
  },  getCSRFToken() {
    const match = document.cookie.match(new RegExp('(^|;)\\\\s*csrftoken=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  },

  async setLanguage(language, switcher, menu, flagId) {
    if (!this.supportedLangs.includes(language)) return;

    this.markActiveLanguage(menu, language);
    this.updateFlagIcon(language);
    switcher.removeAttribute('open');

    const nextUrl = this.buildLanguageUrl(language);

    try {
      const formData = new URLSearchParams();
      formData.set('language', language);
      formData.set('next', nextUrl);

      await fetch('/i18n/setlang/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        },
        credentials: 'same-origin',
        body: formData.toString()
      });
    } catch (error) {
      console.warn('Language switch request failed:', error);
    }

    location.assign(nextUrl);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  LanguageSwitcher.init();
});
