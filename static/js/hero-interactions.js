/**
 * Hero Interactions - Улучшенные эффекты
 * - Upscale: быстрое увеличение и возврат
 * - Canvas: красивый эффект холста
 * - Realtime: длинная плавная анимация живых обоев
 * - Hover на desktop, click на mobile
 * - Полная адаптивность до 320px
 */

class HeroInteractions {
  constructor() {
    this.hero = document.querySelector('[data-hero]');
    if (!this.hero) return;

    this.frame = this.hero.querySelector('.hero-frame');
    this.image = this.frame.querySelector('[data-hero-image]');
    if (!this.image || !this.frame) return;

    this.buttons = this.hero.querySelectorAll('[data-hero-action]');
    this.currentScene = null;
    this.rafId = null;
    this.resetTimer = null;
    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.isMobile = this.checkMobile();

    // Neural style transfer state
    this.originalSrc = this.image.currentSrc || this.image.src;
    this.stylizedDataUrl = null;
    this.styleModel = null;
    this._loadingStyleModel = null;

    this.createOverlays();
    this.bindEvents();

    // Предзагрузка модели стилей (лениво), чтобы эффект Canvas сработал быстрее при первом наведении
    try {
      setTimeout(() => {
        this.ensureStyleModelLoaded && this.ensureStyleModelLoaded().catch(() => {});
      }, 0);
    } catch (_) {}
  }

  checkMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
           || window.innerWidth < 768;
  }

  createOverlays() {
    this.frame.classList.add('hero-visual');

    // Слой шума для realtime
    this.noiseLayer = document.createElement('div');
    this.noiseLayer.className = 'hero-noise-layer';
    this.generateGrainTexture();
    this.frame.appendChild(this.noiseLayer);

    // Слой canvas для эффекта холста
    this.canvasLayer = document.createElement('div');
    this.canvasLayer.className = 'hero-canvas-layer';
    this.generateCanvasTexture();
    this.frame.appendChild(this.canvasLayer);

    // Лоадер для нейростилизации (минимальный, без CSS-файла)
    this.loader = document.createElement('div');
    this.loader.className = 'hero-style-loader';
    this.loader.setAttribute('aria-live', 'polite');
    this.loader.style.position = 'absolute';
    this.loader.style.inset = '0';
    this.loader.style.display = 'none';
    this.loader.style.placeItems = 'center';
    this.loader.style.background = 'rgba(0,0,0,0.15)';
    this.loader.style.color = 'white';
    this.loader.style.fontSize = '12px';
    this.loader.style.fontWeight = '600';
    this.loader.style.letterSpacing = '0.02em';
    this.loader.style.borderRadius = 'inherit';
    this.loader.style.pointerEvents = 'none';
    this.loader.style.backdropFilter = 'blur(2px)';
    this.loader.innerHTML = '<div style="padding:6px 10px;border:1px solid rgba(255,255,255,.3);border-radius:12px;background:rgba(0,0,0,.25)">Загрузка стиля…</div>';
    this.frame.appendChild(this.loader);

    // Слой для готовой «карандашной» версии (по требованию — использовать готовую картинку и анимировать)
    this.pencilLayer = document.createElement('div');
    this.pencilLayer.className = 'hero-pencil-layer';
    Object.assign(this.pencilLayer.style, {
      position: 'absolute',
      inset: '0',
      backgroundImage: 'url(/static/img/bg_pencil_colored.png)',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      borderRadius: 'inherit',
      opacity: '0',
      transform: 'translateY(6px) scale(1.02)',
      transition: 'opacity 700ms cubic-bezier(.2,.7,0,1), transform 800ms cubic-bezier(.2,.7,0,1)',
      zIndex: '3',
      pointerEvents: 'none'
    });
    this.frame.appendChild(this.pencilLayer);
  }

  generateGrainTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');

    // Более детальный шум
    const imageData = ctx.createImageData(400, 400);
    for (let i = 0; i < imageData.data.length; i += 4) {
      const noise = Math.random() * 100;
      imageData.data[i] = noise;
      imageData.data[i + 1] = noise;
      imageData.data[i + 2] = noise;
      imageData.data[i + 3] = 180;
    }
    ctx.putImageData(imageData, 0, 0);

    this.noiseLayer.style.backgroundImage = `url(${canvas.toDataURL()})`;
    this.noiseLayer.style.backgroundSize = '200px 200px';
  }

  generateCanvasTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 800;
    const ctx = canvas.getContext('2d');

    // Базовый цвет холста (бежевый)
    const gradient = ctx.createLinearGradient(0, 0, 800, 800);
    gradient.addColorStop(0, '#f5f0e8');
    gradient.addColorStop(0.5, '#ebe6de');
    gradient.addColorStop(1, '#e8e3db');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 800, 800);

    // Текстура холста - диагональные линии
    ctx.strokeStyle = 'rgba(139, 125, 107, 0.08)';
    ctx.lineWidth = 1;

    // Диагональные линии (/)
    for (let i = -800; i < 1600; i += 3) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i + 800, 800);
      ctx.stroke();
    }

    // Диагональные линии (\)
    for (let i = -800; i < 1600; i += 3) {
      ctx.beginPath();
      ctx.moveTo(i, 800);
      ctx.lineTo(i + 800, 0);
      ctx.stroke();
    }

    // Добавляем органический шум
    const imageData = ctx.getImageData(0, 0, 800, 800);
    for (let i = 0; i < imageData.data.length; i += 4) {
      if (Math.random() > 0.97) {
        const noise = (Math.random() - 0.5) * 30;
        imageData.data[i] += noise;
        imageData.data[i + 1] += noise;
        imageData.data[i + 2] += noise;
      }
    }
    ctx.putImageData(imageData, 0, 0);

    // Виньетка для глубины
    const vignette = ctx.createRadialGradient(400, 400, 100, 400, 400, 600);
    vignette.addColorStop(0, 'rgba(0, 0, 0, 0)');
    vignette.addColorStop(1, 'rgba(0, 0, 0, 0.15)');
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, 800, 800);

    this.canvasLayer.style.backgroundImage = `url(${canvas.toDataURL()})`;
    this.canvasLayer.style.backgroundSize = 'cover';
  }

  bindEvents() {
    this.buttons.forEach(button => {
      const action = button.dataset.heroAction;

      if (this.isMobile) {
        // На мобильных - клик
        button.addEventListener('click', (e) => {
          e.preventDefault();
          this.play(action);
        });
      } else {
        // На desktop - hover
        button.addEventListener('mouseenter', () => {
          this.play(action);
        });
        // Сбрасываем эффект при уходе курсора с кнопки
        button.addEventListener('mouseleave', () => {
          if (this.currentScene === action) this.reset();
        });
      }
    });

    // Сброс при смене вкладки
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.reset();
      }
    });

    // Обновление при ресайзе
    window.addEventListener('resize', () => {
      this.isMobile = this.checkMobile();
    });
  }

  play(action) {
    if (this.currentScene === action) return;

    this.reset();
    this.currentScene = action;
    this.frame.classList.add(`is-${action}-active`);

    if (this.isReducedMotion) {
      this.resetTimer = setTimeout(() => this.reset(), 3000);
      return;
    }

    switch (action) {
      case 'realtime':
        this.playRealtime();
        break;
      case 'canvas':
        this.playCanvas();
        break;
      case 'upscale':
        this.playUpscale();
        break;
    }
  }

  playRealtime() {
    const startScale = 1.0;
    const endScale = 1.08;

    // Mobile: 5 секунд и стоп
    if (this.isMobile) {
      const duration = 5000;
      let startTime = null;
      const animate = (timestamp) => {
        if (!startTime) startTime = timestamp;
        const elapsed = timestamp - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const easeProgress = this.easeInOutQuad(progress);
        const scale = startScale + (endScale - startScale) * easeProgress;

        this.image.style.transformOrigin = '50% 50%';
        this.image.style.transform = `scale(${scale})`;

        if (progress < 1) {
          this.rafId = requestAnimationFrame(animate);
        } else {
          this.reset();
        }
      };
      this.rafId = requestAnimationFrame(animate);
      return;
    }

    // Desktop: бесконечная плавная анимация, пока курсор не уберут (mouseleave сбрасывает)
    const period = 12000; // 12 секунд полный цикл
    const t0 = performance.now();
    const loop = (t) => {
      const elapsed = t - t0;
      const phase = (elapsed % period) / period; // 0..1
      // Синусоидальная пульсация масштаба 1.0..1.08
      const s = (1 - Math.cos(phase * Math.PI * 2)) / 2; // 0..1
      const scale = startScale + (endScale - startScale) * s;

      this.image.style.transformOrigin = '50% 50%';
      this.image.style.transform = `scale(${scale})`;

      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  playCanvas() {
    // Используем готовую «карандашную» картинку и красивую анимацию появления
    const reveal = async () => {
      try {
        await this.preloadPencilImage();
        // стартовое состояние задано в стиле; запускаем анимацию
        this.pencilLayer.style.opacity = '1';
        this.pencilLayer.style.transform = 'translateY(0) scale(1)';
        // Дополнительная лёгкая «бумажная» вибрация масштаба
        const start = performance.now();
        const duration = 800;
        const amp = 0.006; // амплитуда
        const tick = (t) => {
          const p = Math.min(1, (t - start) / duration);
          const ease = 1 - Math.pow(1 - p, 3);
          const wobble = Math.sin(p * Math.PI * 2) * amp * (1 - ease);
          this.pencilLayer.style.transform = `translateY(${(1 - ease) * 6}px) scale(${1 + wobble})`;
          if (p < 1) {
            this.rafId = requestAnimationFrame(tick);
          }
        };
        this.rafId = requestAnimationFrame(tick);
      } catch (e) {
        console.warn('[HeroInteractions] Pencil image preload failed:', e);
      }
    };
    reveal();

    // Автоматический сброс только на mobile
    if (this.isMobile) {
      this.resetTimer = setTimeout(() => this.reset(), 3000);
    }
    // На desktop сброс произойдёт при mouseleave
  }

  playUpscale() {
    const startScale = 1.0;
    const maxScale = 2.0;
    const zoomDuration = 750; // 0.75 сек на увеличение

    // Mobile: автоматический возврат (как было)
    if (this.isMobile) {
      const totalDuration = 1500;
      let startTime = null;

      const animate = (timestamp) => {
        if (!startTime) startTime = timestamp;
        const elapsed = timestamp - startTime;
        const progress = Math.min(elapsed / totalDuration, 1);

        let scale;
        if (elapsed < zoomDuration) {
          // Быстрое увеличение
          const zoomProgress = elapsed / zoomDuration;
          const easeProgress = this.easeOutCubic(zoomProgress);
          scale = startScale + (maxScale - startScale) * easeProgress;
        } else {
          // Быстрое уменьшение
          const shrinkProgress = (elapsed - zoomDuration) / zoomDuration;
          const easeProgress = this.easeInCubic(shrinkProgress);
          scale = maxScale - (maxScale - startScale) * easeProgress;
        }

        this.image.style.transformOrigin = '50% 50%';
        this.image.style.transform = `scale(${scale})`;

        if (progress < 1) {
          this.rafId = requestAnimationFrame(animate);
        } else {
          this.reset();
        }
      };

      this.rafId = requestAnimationFrame(animate);
      return;
    }

    // Desktop: увеличение без автовозврата (возврат только при mouseleave)
    let startTime = null;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / zoomDuration, 1);

      // Только увеличение
      const easeProgress = this.easeOutCubic(progress);
      const scale = startScale + (maxScale - startScale) * easeProgress;

      this.image.style.transformOrigin = '50% 50%';
      this.image.style.transform = `scale(${scale})`;

      if (progress < 1) {
        this.rafId = requestAnimationFrame(animate);
      }
      // НЕ вызываем reset() - изображение остаётся увеличенным
    };

    this.rafId = requestAnimationFrame(animate);
  }

  // Lazy-load TFJS + Magenta model
  loadScript(url) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${url}"]`)) {
        resolve();
        return;
      }
      const s = document.createElement('script');
      s.src = url;
      s.async = true;
      s.onload = resolve;
      s.onerror = () => reject(new Error('Failed to load ' + url));
      document.head.appendChild(s);
    });
  }

  async ensureStyleModelLoaded() {
    if (this.styleModel) return;
    if (this._loadingStyleModel) return this._loadingStyleModel;

    this._loadingStyleModel = (async () => {
      // Load TFJS + Magenta only once
      await this.loadScript('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.13.0/dist/tf.min.js');
      await this.loadScript('https://cdn.jsdelivr.net/npm/@magenta/image@0.3.20/dist/image.min.js');

      if (!window.magenta || !window.magenta.ArbitraryStyleTransferNetwork) {
        throw new Error('Magenta image library not available');
      }

      // Initialize model
      this.styleModel = new window.magenta.ArbitraryStyleTransferNetwork();
      await this.styleModel.initialize();
    })();

    return this._loadingStyleModel;
  }

  ensureImageLoaded(imgEl) {
    return new Promise((resolve, reject) => {
      if (!imgEl) return reject(new Error('Image element is null'));
      if (imgEl.complete && imgEl.naturalWidth > 0) return resolve();
      imgEl.addEventListener('load', () => resolve(), { once: true });
      imgEl.addEventListener('error', () => reject(new Error('Failed to load image')), { once: true });
    });
  }

  async getStyleImageElement() {
    // Используем процедурно сгенерированный стиль «ландшафтное масло»
    // (стабильный, без CORS, даёт “настоящие” мазки и палитру пейзажа)
    const url = this.landscapeStyleUrl || (this.landscapeStyleUrl = this.createLandscapeStyleDataUrl());
    const styleEl = new Image();
    styleEl.src = url; // data: URL — загружается мгновенно
    await this.ensureImageLoaded(styleEl);
    return styleEl;
  }

  async stylizeCurrentImage() {
    let applied = false;
    try {
      if (this.loader) this.loader.style.display = 'grid';

      // Если уже есть кэшированный результат стилизации — используем его без повторного инференса
      if (this.stylizedDataUrl) {
        if (!this.originalSrc) {
          this.originalSrc = this.image.currentSrc || this.image.src;
        }
        this.image.src = this.stylizedDataUrl;
        console.info('[HeroInteractions] Using cached stylized image');
        applied = true;
        return;
      }

      // Эффект «карандашный рисунок» с сохранением исходных цветов — без AST
      // (точь-в-точь композиция, добавляем штриховку/линию по luminance)
      await this.ensureImageLoaded(this.image);
      const pencilUrl = await this.applyPencilSketchFromImage(this.image);
      this.stylizedDataUrl = pencilUrl;
      if (!this.originalSrc) {
        this.originalSrc = this.image.currentSrc || this.image.src;
      }
      this.image.src = this.stylizedDataUrl;
      console.info('[HeroInteractions] Pencil sketch applied');
      applied = true;
      return;

      // Преобразовать результат в Canvas и затем в dataURL
      let dataUrl = null;
      try {
        if (output instanceof HTMLCanvasElement) {
          let canv = output;
          try { canv = this.applyOilPaintToCanvas(canv, 6, 16); } catch(_) {}
          dataUrl = canv.toDataURL('image/webp', 0.92);
        } else if (output instanceof ImageData) {
          const c = document.createElement('canvas');
          c.width = output.width;
          c.height = output.height;
          const ctx = c.getContext('2d');
          ctx.putImageData(output, 0, 0);
          try { this.applyOilPaintToCanvas(c, 6, 16); } catch(_) {}
          dataUrl = c.toDataURL('image/webp', 0.92);
        } else if (output && output.shape && window.tf && tf.browser && typeof tf.browser.toPixels === 'function') {
          // tf.Tensor3D -> canvas
          const [h, w] = [output.shape[0], output.shape[1]];
          const c = document.createElement('canvas');
          c.width = w;
          c.height = h;
          await tf.browser.toPixels(output, c);
          if (typeof output.dispose === 'function') output.dispose();
          try { this.applyOilPaintToCanvas(c, 6, 16); } catch(_) {}
          dataUrl = c.toDataURL('image/webp', 0.92);
        }
      } catch (convErr) {
        console.warn('[HeroInteractions] Failed to convert stylization output:', convErr);
      }

      // Если модель/конвертация не дали результат — используем быстрый JS fallback
      if (!dataUrl) {
        try {
          dataUrl = await this.applyPainterlyFallback(this.image);
        } catch (fbErr) {
          console.warn('[HeroInteractions] Painterly fallback failed:', fbErr);
        }
      }

      this.stylizedDataUrl = dataUrl;
      // Сохраним оригинал только один раз и подменим картинку, если конвертация удалась
      if (this.stylizedDataUrl) {
        if (!this.originalSrc) {
          this.originalSrc = this.image.currentSrc || this.image.src;
        }
        this.image.src = this.stylizedDataUrl;
        console.info('[HeroInteractions] Magenta stylization applied');
        applied = true;
      }
    } catch (err) {
      // Если что-то пошло не так — пробуем JS-fallback, иначе остаёмся на оверлее холста
      console.warn('[HeroInteractions] Stylization failed, trying fallback:', err);
      try {
        const dataUrl = await this.applyPainterlyFallback(this.image);
        if (dataUrl) {
          this.stylizedDataUrl = dataUrl;
          if (!this.originalSrc) {
            this.originalSrc = this.image.currentSrc || this.image.src;
          }
          this.image.src = this.stylizedDataUrl;
          console.info('[HeroInteractions] Painterly fallback applied');
          applied = true;
        }
      } catch (_) {}
    } finally {
      if (this.loader) this.loader.style.display = 'none';
    }
    return applied;
  }

  /**
   * Процедурный генератор «ландшафтного масляного» стиля (brush map).
   * Палитра и мазки подобраны под пейзаж: небо/облака/дерево/трава/почва.
   * Результат используется как style-изображение для Magenta AST.
   */
  createLandscapeStyleDataUrl() {
    const W = 512, H = 512;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const ctx = c.getContext('2d');

    // База: мягкий градиент неба (верх 60%) и земли (низ 40%)
    const skyH = Math.floor(H * 0.6);
    const gSky = ctx.createLinearGradient(0, 0, 0, skyH);
    gSky.addColorStop(0, '#9EC9FF');   // светло-голубой
    gSky.addColorStop(1, '#CFE8FF');   // молочный голубой
    ctx.fillStyle = gSky;
    ctx.fillRect(0, 0, W, skyH);

    const gGround = ctx.createLinearGradient(0, skyH, 0, H);
    gGround.addColorStop(0, '#88B36B'); // зелень
    gGround.addColorStop(1, '#5A8F46'); // тени травы
    ctx.fillStyle = gGround;
    ctx.fillRect(0, skyH, W, H - skyH);

    // Функция одного мазка
    const stroke = (x, y, len, angle, color, alpha, width) => {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = color;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.lineWidth = width;
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.beginPath();
      ctx.moveTo(-len / 2, 0);
      ctx.lineTo(len / 2, 0);
      ctx.stroke();
      ctx.restore();
    };

    // Мазки облаков (мягкие, светлые)
    for (let i = 0; i < 220; i++) {
      const x = Math.random() * W;
      const y = Math.random() * (skyH * 0.8);
      const len = 20 + Math.random() * 90;
      const ang = (Math.random() - 0.5) * 0.4;
      const a = 0.06 + Math.random() * 0.09;
      const w = 6 + Math.random() * 14;
      const shades = ['#FFFFFF', '#F7FBFF', '#EEF6FF', '#E4F0FF'];
      const col = shades[Math.floor(Math.random() * shades.length)];
      stroke(x, y, len, ang, col, a, w);
    }

    // Мазки света над горизонтом (тёплые блики)
    for (let i = 0; i < 120; i++) {
      const x = Math.random() * W;
      const y = skyH - 20 + Math.random() * 40;
      const len = 15 + Math.random() * 60;
      const ang = (Math.random() - 0.5) * 0.8;
      const a = 0.05 + Math.random() * 0.08;
      const w = 4 + Math.random() * 10;
      const col = '#E7C68C';
      stroke(x, y, len, ang, col, a, w);
    }

    // Травяные мазки (нижняя часть)
    for (let i = 0; i < 260; i++) {
      const x = Math.random() * W;
      const y = skyH + Math.random() * (H - skyH);
      const len = 10 + Math.random() * 55;
      const ang = (Math.random() - 0.5) * 0.9;
      const a = 0.08 + Math.random() * 0.12;
      const w = 3 + Math.random() * 9;
      const greens = ['#6FAF56', '#5D9C48', '#79BA62', '#4F8A3E'];
      const col = greens[Math.floor(Math.random() * greens.length)];
      stroke(x, y, len, ang, col, a, w);
    }

    // Древесные/тёмные мазки (силуэты деревьев)
    for (let i = 0; i < 140; i++) {
      const x = Math.random() * W;
      const y = skyH - 30 + Math.random() * ((H - skyH) + 60);
      const len = 8 + Math.random() * 45;
      const ang = (Math.random() - 0.5) * 1.2;
      const a = 0.06 + Math.random() * 0.1;
      const w = 2 + Math.random() * 7;
      const woods = ['#2E4D2C', '#3A5B39', '#264424'];
      const col = woods[Math.floor(Math.random() * woods.length)];
      stroke(x, y, len, ang, col, a, w);
    }

    // Дополнительные прохладные тени в небе
    for (let i = 0; i < 80; i++) {
      const x = Math.random() * W;
      const y = Math.random() * (skyH * 0.9);
      const len = 12 + Math.random() * 50;
      const ang = (Math.random() - 0.5) * 0.7;
      const a = 0.04 + Math.random() * 0.06;
      const w = 3 + Math.random() * 8;
      const col = '#B9D7FF';
      stroke(x, y, len, ang, col, a, w);
    }

    // Лёгкая текстура холста
    const noise = document.createElement('canvas');
    noise.width = W; noise.height = H;
    const nctx = noise.getContext('2d');
    const nimg = nctx.createImageData(W, H);
    for (let i = 0; i < nimg.data.length; i += 4) {
      const v = 245 + Math.floor(Math.random() * 10); // слабый шум
      nimg.data[i] = v; nimg.data[i+1] = v; nimg.data[i+2] = v; nimg.data[i+3] = 18;
    }
    nctx.putImageData(nimg, 0, 0);
    ctx.globalCompositeOperation = 'multiply';
    ctx.drawImage(noise, 0, 0);
    ctx.globalCompositeOperation = 'source-over';

    return c.toDataURL('image/png');
  }

  /**
   * Фильтр «масляная живопись» — усиливает мазки, делает картинку максимально похожей на картину.
   * radius — радиус окна, levels — количество корзин яркости (чем больше, тем тоньше мазки).
   */
  applyOilPaintToCanvas(canvas, radius = 6, levels = 16) {
    const w = canvas.width, h = canvas.height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const src = ctx.getImageData(0, 0, w, h);
    const s = src.data;
    const dst = ctx.createImageData(w, h);
    const d = dst.data;

    const binsR = new Uint32Array(levels);
    const binsG = new Uint32Array(levels);
    const binsB = new Uint32Array(levels);
    const binsC = new Uint32Array(levels);

    const clamp = (v, min, max) => v > max ? max : (v < min ? min : v);

    // Копируем границы без обработки
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = (y * w + x) * 4;
        if (x < radius || y < radius || x >= w - radius || y >= h - radius) {
          d[idx] = s[idx]; d[idx+1] = s[idx+1]; d[idx+2] = s[idx+2]; d[idx+3] = s[idx+3];
        }
      }
    }

    for (let y = radius; y < h - radius; y++) {
      for (let x = radius; x < w - radius; x++) {
        binsR.fill(0); binsG.fill(0); binsB.fill(0); binsC.fill(0);

        // Собираем статистику по окну
        for (let j = -radius; j <= radius; j++) {
          let yy = y + j;
          for (let i = -radius; i <= radius; i++) {
            let xx = x + i;
            const o = (yy * w + xx) * 4;
            const r = s[o], g = s[o+1], b = s[o+2];
            const lum = (0.299 * r + 0.587 * g + 0.114 * b) | 0;
            const bin = clamp((lum * levels / 256) | 0, 0, levels - 1);
            binsR[bin] += r;
            binsG[bin] += g;
            binsB[bin] += b;
            binsC[bin] += 1;
          }
        }

        // Находим «самый популярный» бокс яркости и усредняем его цвет
        let bestBin = 0, bestCount = 0;
        for (let k = 0; k < levels; k++) {
          if (binsC[k] > bestCount) { bestCount = binsC[k]; bestBin = k; }
        }

        const idx = (y * w + x) * 4;
        if (bestCount > 0) {
          d[idx]   = (binsR[bestBin] / bestCount) | 0;
          d[idx+1] = (binsG[bestBin] / bestCount) | 0;
          d[idx+2] = (binsB[bestBin] / bestCount) | 0;
          d[idx+3] = 255;
        } else {
          d[idx] = s[idx]; d[idx+1] = s[idx+1]; d[idx+2] = s[idx+2]; d[idx+3] = s[idx+3];
        }
      }
    }

    ctx.putImageData(dst, 0, 0);

    // Лёгкий финальный грейдинг для «тёплого пейзажа»
    try {
      const filtered = document.createElement('canvas');
      filtered.width = w; filtered.height = h;
      const fctx = filtered.getContext('2d');
      fctx.filter = 'saturate(1.15) contrast(1.1) brightness(1.03) hue-rotate(5deg)';
      fctx.drawImage(canvas, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(filtered, 0, 0);
    } catch (_) {}
    return canvas;
  }

  /**
   * Карандашный скетч с сохранением цвета:
   * 1) Получаем градации серого, размываем.
   * 2) Color Dodge (серый, инверсия размытого) -> штриховка/бумага.
   * 3) Перемножаем исходные цвета на полученную «бумагу» (сохраняем палитру).
   */
  async applyPencilSketchFromImage(imgEl) {
    await this.ensureImageLoaded(imgEl);

    // Базовый канвас
    const base = document.createElement('canvas');
    const maxW = 1024, maxH = 1024;
    let w = imgEl.naturalWidth || imgEl.width || 800;
    let h = imgEl.naturalHeight || imgEl.height || 600;
    const r = Math.min(1, maxW / w, maxH / h);
    w = Math.max(1, Math.round(w * r));
    h = Math.max(1, Math.round(h * r));
    base.width = w; base.height = h;
    const bctx = base.getContext('2d', { willReadFrequently: true });
    bctx.drawImage(imgEl, 0, 0, w, h);

    // Градации серого
    const grayCanv = document.createElement('canvas');
    grayCanv.width = w; grayCanv.height = h;
    const gctx = grayCanv.getContext('2d', { willReadFrequently: true });
    gctx.drawImage(base, 0, 0);
    const gImg = gctx.getImageData(0, 0, w, h);
    const gp = gImg.data;
    for (let i = 0; i < gp.length; i += 4) {
      const r = gp[i], g = gp[i+1], b = gp[i+2];
      const L = (0.299 * r + 0.587 * g + 0.114 * b) | 0;
      gp[i] = gp[i+1] = gp[i+2] = L;
    }
    gctx.putImageData(gImg, 0, 0);

    // Размытие серого (Gaussian approximation через canvas filter)
    const blurCanv = document.createElement('canvas');
    blurCanv.width = w; blurCanv.height = h;
    const blctx = blurCanv.getContext('2d', { willReadFrequently: true });
    blctx.filter = 'blur(6px)';
    blctx.drawImage(grayCanv, 0, 0);

    const blurred = blctx.getImageData(0, 0, w, h).data;
    const src = bctx.getImageData(0, 0, w, h);
    const sp = src.data;

    // Выходной канвас
    const out = bctx.createImageData(w, h);
    const op = out.data;

    // Color Dodge на основе серого и размытого (инверсии)
    for (let i = 0; i < sp.length; i += 4) {
      const r0 = sp[i], g0 = sp[i+1], b0 = sp[i+2];
      // Берём L исходника из уже посчитанного gray
      const L = (0.299 * r0 + 0.587 * g0 + 0.114 * b0) | 0;
      const Bl = blurred[i]; // blurred gray

      // Dodge: Ld = min(255, (L << 8) / (256 - Bl + 1))
      let Ld = (L << 8) / (256 - Bl + 1);
      if (Ld > 255) Ld = 255;

      // Нормируем как фактор бумаги (0..1), легкий гамма-корректор для мягкости
      let paper = Ld / 255;
      paper = Math.pow(paper, 0.85);

      // Сохраняем цвета — перемножаем исходный цвет на «бумагу»
      op[i]   = Math.max(0, Math.min(255, r0 * paper));
      op[i+1] = Math.max(0, Math.min(255, g0 * paper));
      op[i+2] = Math.max(0, Math.min(255, b0 * paper));
      op[i+3] = 255;
    }

    bctx.putImageData(out, 0, 0);

    // Лёгкая имитация зерна бумаги (очень мягко)
    try {
      const paper = document.createElement('canvas');
      paper.width = w; paper.height = h;
      const pctx = paper.getContext('2d');
      const n = pctx.createImageData(w, h);
      for (let i = 0; i < n.data.length; i += 4) {
        const v = 250 + ((Math.random() * 10) | 0);
        n.data[i] = v; n.data[i+1] = v; n.data[i+2] = v; n.data[i+3] = 10;
      }
      pctx.putImageData(n, 0, 0);
      bctx.globalCompositeOperation = 'multiply';
      bctx.drawImage(paper, 0, 0);
      bctx.globalCompositeOperation = 'source-over';
    } catch(_) {}

    return base.toDataURL('image/webp', 0.92);
  }

  /**
   * JS fallback «painterly»: быстрый постеризованный вид с лёгким контуром.
   * Не нейросеть, но создаёт заметный «нарисованный» стиль, если модель недоступна.
   */
  async applyPainterlyFallback(imgEl) {
    await this.ensureImageLoaded(imgEl);
    const tmp = document.createElement('canvas');
    // Умеренно уменьшаем разрешение для скорости
    const maxW = 800, maxH = 800;
    let w = imgEl.naturalWidth || imgEl.width || 800;
    let h = imgEl.naturalHeight || imgEl.height || 600;
    const r = Math.min(1, maxW / w, maxH / h);
    w = Math.max(1, Math.round(w * r));
    h = Math.max(1, Math.round(h * r));
    tmp.width = w;
    tmp.height = h;

    const ctx = tmp.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(imgEl, 0, 0, w, h);

    // Постеризация + лёгкий шум
    let img = ctx.getImageData(0, 0, w, h);
    let d = img.data;
    const levels = 5; // уровни постеризации на канал (сильнее эффект)
    for (let i = 0; i < d.length; i += 4) {
      for (let c = 0; c < 3; c++) {
        const v = d[i + c] / 255;
        const q = Math.round(v * (levels - 1)) / (levels - 1);
        let val = Math.round(q * 255);
        // лёгкий шум кисти (усиленный, чтобы эффект был заметнее)
        val = Math.min(255, Math.max(0, val + (Math.random() * 12 - 6)));
        d[i + c] = val;
      }
      // слегка усилим контраст
      d[i] = Math.min(255, d[i] * 1.05);
      d[i + 1] = Math.min(255, d[i + 1] * 1.05);
      d[i + 2] = Math.min(255, d[i + 2] * 1.05);
    }
    ctx.putImageData(img, 0, 0);

    // Быстрый фильтр через canvas filter для усиления «краски»
    try {
      const filtered = document.createElement('canvas');
      filtered.width = w; filtered.height = h;
      const fctx = filtered.getContext('2d');
      // Чуть больше насыщенности/контраста/яркости
      fctx.filter = 'saturate(1.25) contrast(1.2) brightness(1.05)';
      fctx.drawImage(tmp, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(filtered, 0, 0);
    } catch (_) {}

    // Простой контур (Собель)
    const kx = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
    const ky = [-1, -2, -1, 0, 0, 0, 1, 2, 1];
    const src = ctx.getImageData(0, 0, w, h);
    const s = src.data;
    const edge = ctx.createImageData(w, h);
    const e = edge.data;

    const lum = new Float32Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = (y * w + x) * 4;
        lum[y * w + x] = 0.299 * s[idx] + 0.587 * s[idx + 1] + 0.114 * s[idx + 2];
      }
    }

    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        let gx = 0, gy = 0, t = 0;
        let p = 0;
        for (let j = -1; j <= 1; j++) {
          for (let i = -1; i <= 1; i++) {
            const v = lum[(y + j) * w + (x + i)];
            gx += v * kx[p];
            gy += v * ky[p];
            p++;
          }
        }
        t = Math.sqrt(gx * gx + gy * gy);
        const o = (y * w + x) * 4;
        // тонкий тёмный контур
        const v = Math.max(0, 255 - t * 1.4); // усилить контуры
        e[o] = v; e[o + 1] = v; e[o + 2] = v; e[o + 3] = 255;
      }
    }

    // Наложим контур в режиме multiply
    const edgeCanvas = document.createElement('canvas');
    edgeCanvas.width = w; edgeCanvas.height = h;
    edgeCanvas.getContext('2d').putImageData(edge, 0, 0);
    ctx.globalAlpha = 0.85; // сделать контур заметнее
    ctx.globalCompositeOperation = 'multiply';
    ctx.drawImage(edgeCanvas, 0, 0);
    ctx.globalCompositeOperation = 'source-over';

    return tmp.toDataURL('image/webp', 0.9);
  }

  // Прелоад готовой «карандашной» версии
  preloadPencilImage() {
    if (this._pencilLoaded) return Promise.resolve();
    if (this._loadingPencil) return this._loadingPencil;
    this._loadingPencil = new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => { this._pencilLoaded = true; resolve(); };
      img.onerror = reject;
      img.src = '/static/img/bg_pencil_colored.png';
    });
    return this._loadingPencil;
  }

  // Easing функции
  easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }

  easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  easeInCubic(t) {
    return t * t * t;
  }

  reset() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    if (this.resetTimer) {
      clearTimeout(this.resetTimer);
      this.resetTimer = null;
    }

    // Вернуть исходное изображение, если было стилизовано
    if (this.stylizedDataUrl && this.originalSrc) {
      try {
        if ((this.image.currentSrc || this.image.src) !== this.originalSrc) {
          this.image.src = this.originalSrc;
        }
      } catch (_) {
        this.image.src = this.originalSrc;
      }
    }

    this.currentScene = null;
    this.frame.classList.remove('is-realtime-active', 'is-canvas-active', 'is-upscale-active');

    // Спрятать «карандашный» слой и вернуть стартовый трансформ
    if (this.pencilLayer) {
      this.pencilLayer.style.opacity = '0';
      this.pencilLayer.style.transform = 'translateY(6px) scale(1.02)';
    }

    this.image.style.transform = '';
    this.image.style.transformOrigin = '';
  }
}

/**
 * Инициализация:
 * Если DOM уже загружен (скрипт подключён внизу), сразу запускаем.
 * Иначе ждём DOMContentLoaded.
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new HeroInteractions();
  });
} else {
  new HeroInteractions();
}
