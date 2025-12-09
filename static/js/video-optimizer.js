/**
 * Модуль оптимизации и сжатия видео
 * Обеспечивает эффективную загрузку и отображение видео
 */

class VideoOptimizer {
  constructor() {
    this.compressionQuality = 0.8;
    this.maxWidth = 1920;
    this.maxHeight = 1080;
  }

  /**
   * Генерация thumbnail из видео
   * @param {string} videoUrl - URL видео
   * @param {number} timeOffset - Время в секундах для захвата кадра
   * @returns {Promise<string>} - Data URL thumbnail
   */
  async generateThumbnail(videoUrl, timeOffset = 1) {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video');
      video.crossOrigin = 'anonymous';
      video.preload = 'metadata';

      video.addEventListener('loadedmetadata', () => {
        // Устанавливаем время для захвата кадра
        video.currentTime = Math.min(timeOffset, video.duration / 2);
      });

      video.addEventListener('seeked', () => {
        try {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');

          // Устанавливаем размер canvas
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;

          // Рисуем кадр
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          // Конвертируем в data URL
          const thumbnail = canvas.toDataURL('image/jpeg', 0.8);
          resolve(thumbnail);
        } catch (error) {
          reject(error);
        }
      });

      video.addEventListener('error', (e) => {
        reject(new Error('Ошибка загрузки видео для thumbnail'));
      });

      video.src = videoUrl;
    });
  }

  /**
   * Lazy loading для видео элементов
   * @param {HTMLVideoElement} videoElement - Видео элемент
   */
  lazyLoad(videoElement) {
    if (!videoElement) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const video = entry.target;
          const source = video.querySelector('source');

          if (source && source.dataset.src) {
            source.src = source.dataset.src;
            video.load();
            observer.unobserve(video);
          }
        }
      });
    }, {
      rootMargin: '50px'
    });

    observer.observe(videoElement);
  }

  /**
   * Предзагрузка видео с прогрессом
   * @param {string} videoUrl - URL видео
   * @param {Function} onProgress - Callback для прогресса (0-100)
   * @returns {Promise<Blob>} - Blob видео
   */
  async preloadWithProgress(videoUrl, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open('GET', videoUrl, true);
      xhr.responseType = 'blob';

      xhr.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percentComplete = (event.loaded / event.total) * 100;
          onProgress(percentComplete);
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          resolve(xhr.response);
        } else {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error('Ошибка загрузки видео'));
      xhr.send();
    });
  }

  /**
   * Создание оптимизированного видео элемента
   * @param {string} videoUrl - URL видео
   * @param {object} options - Опции (autoplay, loop, muted, controls)
   * @returns {HTMLVideoElement}
   */
  createOptimizedVideo(videoUrl, options = {}) {
    const video = document.createElement('video');

    // Настройки по умолчанию
    const defaults = {
      autoplay: false,
      loop: false,
      muted: false,
      controls: true,
      preload: 'metadata',
      playsinline: true
    };

    const settings = { ...defaults, ...options };

    // Применяем настройки
    Object.keys(settings).forEach(key => {
      if (typeof settings[key] === 'boolean') {
        if (settings[key]) video.setAttribute(key, '');
      } else {
        video.setAttribute(key, settings[key]);
      }
    });

    // Добавляем source
    const source = document.createElement('source');
    source.src = videoUrl;
    source.type = 'video/mp4';
    video.appendChild(source);

    // Стили для оптимизации
    video.style.width = '100%';
    video.style.height = 'auto';
    video.style.maxWidth = '100%';

    return video;
  }

  /**
   * Проверка поддержки формата видео
   * @param {string} mimeType - MIME тип (например, 'video/mp4')
   * @returns {boolean}
   */
  canPlayType(mimeType) {
    const video = document.createElement('video');
    return video.canPlayType(mimeType) !== '';
  }

  /**
   * Получение информации о видео
   * @param {string} videoUrl - URL видео
   * @returns {Promise<object>} - Информация о видео
   */
  async getVideoInfo(videoUrl) {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video');
      video.preload = 'metadata';
      video.crossOrigin = 'anonymous';

      video.addEventListener('loadedmetadata', () => {
        const info = {
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
          aspectRatio: (video.videoWidth / video.videoHeight).toFixed(2)
        };
        resolve(info);
      });

      video.addEventListener('error', () => {
        reject(new Error('Не удалось загрузить метаданные видео'));
      });

      video.src = videoUrl;
    });
  }

  /**
   * Адаптивное качество видео на основе соединения
   * @returns {string} - Рекомендуемое качество ('high', 'medium', 'low')
   */
  getRecommendedQuality() {
    if (!navigator.connection) return 'high';

    const connection = navigator.connection;
    const effectiveType = connection.effectiveType;

    // 4G или лучше - высокое качество
    if (effectiveType === '4g' || effectiveType === '5g') {
      return 'high';
    }
    // 3G - среднее качество
    else if (effectiveType === '3g') {
      return 'medium';
    }
    // 2G или медленнее - низкое качество
    else {
      return 'low';
    }
  }

  /**
   * Оптимизация видео для отображения
   * @param {HTMLVideoElement} videoElement - Видео элемент
   */
  optimizeForDisplay(videoElement) {
    if (!videoElement) return;

    // Отключаем предзагрузку для экономии трафика
    videoElement.preload = 'metadata';

    // Включаем аппаратное ускорение
    videoElement.style.transform = 'translateZ(0)';
    videoElement.style.willChange = 'transform';

    // Оптимизация для мобильных
    if (this.isMobile()) {
      videoElement.setAttribute('playsinline', '');
      videoElement.setAttribute('webkit-playsinline', '');
    }

    // Обработка ошибок
    videoElement.addEventListener('error', (e) => {
      console.error('Ошибка воспроизведения видео:', e);
      this.showVideoError(videoElement);
    });

    // Показываем индикатор загрузки
    videoElement.addEventListener('waiting', () => {
      this.showLoadingIndicator(videoElement);
    });

    videoElement.addEventListener('canplay', () => {
      this.hideLoadingIndicator(videoElement);
    });
  }

  /**
   * Проверка мобильного устройства
   */
  isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Показать индикатор загрузки
   */
  showLoadingIndicator(videoElement) {
    const container = videoElement.parentElement;
    if (!container) return;

    let loader = container.querySelector('.video-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.className = 'video-loader absolute inset-0 flex items-center justify-center bg-black/50';
      loader.innerHTML = `
        <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      `;
      container.style.position = 'relative';
      container.appendChild(loader);
    }
    loader.style.display = 'flex';
  }

  /**
   * Скрыть индикатор загрузки
   */
  hideLoadingIndicator(videoElement) {
    const container = videoElement.parentElement;
    if (!container) return;

    const loader = container.querySelector('.video-loader');
    if (loader) {
      loader.style.display = 'none';
    }
  }

  /**
   * Показать ошибку видео
   */
  showVideoError(videoElement) {
    const container = videoElement.parentElement;
    if (!container) return;

    const error = document.createElement('div');
    error.className = 'absolute inset-0 flex items-center justify-center bg-black/80 text-white p-4 text-center';
    error.innerHTML = `
      <div>
        <svg class="w-12 h-12 mx-auto mb-2 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p class="text-sm">Ошибка загрузки видео</p>
      </div>
    `;
    container.appendChild(error);
  }

  /**
   * Создание адаптивного видео плеера
   * @param {string} videoUrl - URL видео
   * @param {HTMLElement} container - Контейнер для плеера
   */
  createResponsivePlayer(videoUrl, container) {
    if (!container) return;

    const quality = this.getRecommendedQuality();
    const video = this.createOptimizedVideo(videoUrl, {
      controls: true,
      preload: quality === 'low' ? 'none' : 'metadata'
    });

    this.optimizeForDisplay(video);
    container.appendChild(video);

    return video;
  }
}

/**
 * Дополнения: ленивое «гидрирование» видеокарт в витрине
 * - Ничего не ломаем: работаем только при наличии data-src либо мягко переводим существующий src в data-src
 * - preload='none' до пересечения с вьюпортом
 * - Используем уже существующий lazyLoad() через IntersectionObserver
 */

// Расширения прототипа, чтобы не править тело класса
VideoOptimizer.prototype.ensureLazyForVideo = function(videoElement) {
  if (!videoElement || !(videoElement instanceof HTMLVideoElement)) return;

  try {
    // Никогда не тянем весь файл заранее
    videoElement.preload = 'none';
    videoElement.removeAttribute('autoplay');
    videoElement.setAttribute('playsinline', '');
    videoElement.muted = videoElement.muted || false; // оставляем как есть, но исключаем авто-плей

    // Если у видео нет <source>, но есть src — переводим src в data-src на source
    let source = videoElement.querySelector('source');
    if (!source) {
      const currentSrc = videoElement.getAttribute('src');
      if (currentSrc) {
        videoElement.removeAttribute('src');
        source = document.createElement('source');
        source.dataset.src = currentSrc;
        source.type = 'video/mp4';
        videoElement.appendChild(source);
      }
    } else {
      // Если source.src уже задан — переносим его в data-src
      if (source.getAttribute('src') && !source.dataset.src) {
        source.dataset.src = source.getAttribute('src');
        source.removeAttribute('src');
      }
    }

    // Поддержка постера, если задан через data-poster
    const poster = videoElement.getAttribute('data-poster');
    if (poster && !videoElement.getAttribute('poster')) {
      videoElement.setAttribute('poster', poster);
    }

    // Красивая оптимизация отображения
    this.optimizeForDisplay(videoElement);

    // Настраиваем ленивую загрузку только если есть data-src
    const srcHasData = !!(source && source.dataset && source.dataset.src);
    if (srcHasData) {
      this.lazyLoad(videoElement);
    }
  } catch (_) { /* no-op */ }
};

VideoOptimizer.prototype.hydrateContainer = function(selector) {
  try {
    const root = (typeof selector === 'string') ? document.querySelector(selector) : selector;
    if (!root) return;
    const videos = root.querySelectorAll('video');
    videos.forEach(v => this.ensureLazyForVideo(v));
  } catch (_) { /* silent */ }
};

// Инициализация глобального экземпляра
window.videoOptimizer = new VideoOptimizer();

console.log('VideoOptimizer модуль загружен');

// Автоматическое подключение ленивой подгрузки для витрин (публичной и админ)
(function () {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapLazyVideos);
  } else {
    bootstrapLazyVideos();
  }

  function bootstrapLazyVideos() {
    const vo = window.videoOptimizer;
    if (!vo) return;

    // Основные контейнеры: публичная витрина видео и админ-галерея
    const targets = ['#videoShowcaseSection', '#vaGrid'];
    targets.forEach(sel => vo.hydrateContainer(sel));

    // Следим за динамическими вставками карточек (пагинация, догрузка)
    targets.forEach(sel => {
      const root = document.querySelector(sel);
      if (!root || !('MutationObserver' in window)) return;
      const mo = new MutationObserver((mutations) => {
        for (const m of mutations) {
          if (m.addedNodes && m.addedNodes.length) {
            // Гидрировать только добавленные узлы
            m.addedNodes.forEach(node => {
              if (node && node.querySelectorAll) {
                vo.hydrateContainer(node);
              } else if (node instanceof HTMLVideoElement) {
                vo.ensureLazyForVideo(node);
              }
            });
          }
        }
      });
      mo.observe(root, { childList: true, subtree: true });
    });
  }
})();
