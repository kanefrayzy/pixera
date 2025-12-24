/**
 * Модуль кеширования видео в IndexedDB
 * Хранит видео локально в браузере с TTL 24 часа
 */

class VideoCache {
  constructor() {
    this.dbName = 'AIGalleryVideoCache';
    this.storeName = 'videos';
    this.version = 1;
    this.db = null;
    
    this.init();
  }

  /**
   * Инициализация IndexedDB
   */
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => {
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.clearExpired(); // Очищаем устаревшие при старте
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        // Создаем хранилище если его нет
        if (!db.objectStoreNames.contains(this.storeName)) {
          const objectStore = db.createObjectStore(this.storeName, { keyPath: 'jobId' });
          objectStore.createIndex('expiresAt', 'expiresAt', { unique: false });
          objectStore.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
    });
  }

  /**
   * Сохранить видео в кеш
   * @param {number} jobId - ID задачи
   * @param {string} videoUrl - URL видео
   * @param {string} expiresAt - ISO дата истечения
   */
  async store(jobId, videoUrl, expiresAt) {
    if (!this.db) await this.init();

    const expiryDate = expiresAt ? new Date(expiresAt) : new Date(Date.now() + 24 * 60 * 60 * 1000);

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const objectStore = transaction.objectStore(this.storeName);

      const data = {
        jobId: jobId,
        videoUrl: videoUrl,
        expiresAt: expiryDate.getTime(),
        createdAt: Date.now(),
        size: 0 // Размер будем вычислять при необходимости
      };

      const request = objectStore.put(data);

      request.onsuccess = () => {
        resolve(data);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Получить видео из кеша
   * @param {number} jobId - ID задачи
   * @returns {Promise<object|null>} - Данные видео или null
   */
  async get(jobId) {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readonly');
      const objectStore = transaction.objectStore(this.storeName);
      const request = objectStore.get(jobId);

      request.onsuccess = () => {
        const data = request.result;
        
        if (!data) {
          resolve(null);
          return;
        }

        // Проверяем не истек ли срок
        if (data.expiresAt < Date.now()) {
          this.clear(jobId);
          resolve(null);
          return;
        }

        resolve(data);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Удалить видео из кеша
   * @param {number} jobId - ID задачи
   */
  async clear(jobId) {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const objectStore = transaction.objectStore(this.storeName);
      const request = objectStore.delete(jobId);

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Очистить все устаревшие видео
   */
  async clearExpired() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const objectStore = transaction.objectStore(this.storeName);
      const index = objectStore.index('expiresAt');
      
      const now = Date.now();
      const range = IDBKeyRange.upperBound(now);
      const request = index.openCursor(range);

      let deletedCount = 0;

      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          cursor.delete();
          deletedCount++;
          cursor.continue();
        } else {
          resolve(deletedCount);
        }
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Получить все видео из кеша
   */
  async getAll() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readonly');
      const objectStore = transaction.objectStore(this.storeName);
      const request = objectStore.getAll();

      request.onsuccess = () => {
        const videos = request.result.filter(v => v.expiresAt > Date.now());
        resolve(videos);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Получить размер кеша в байтах (приблизительно)
   */
  async getCacheSize() {
    const videos = await this.getAll();
    return videos.reduce((total, video) => total + (video.size || 0), 0);
  }

  /**
   * Очистить весь кеш
   */
  async clearAll() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const objectStore = transaction.objectStore(this.storeName);
      const request = objectStore.clear();

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Получить статистику кеша
   */
  async getStats() {
    const videos = await this.getAll();
    const totalSize = await this.getCacheSize();
    
    return {
      count: videos.length,
      totalSize: totalSize,
      totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
      oldestVideo: videos.length > 0 ? new Date(Math.min(...videos.map(v => v.createdAt))) : null,
      newestVideo: videos.length > 0 ? new Date(Math.max(...videos.map(v => v.createdAt))) : null
    };
  }
}

// Инициализация глобального экземпляра
window.videoCache = new VideoCache();

// Автоматическая очистка устаревших видео каждый час
setInterval(() => {
  if (window.videoCache) {
    window.videoCache.clearExpired();
  }
}, 60 * 60 * 1000);

// Очистка при закрытии страницы (опционально)
window.addEventListener('beforeunload', () => {
  if (window.videoCache) {
    window.videoCache.clearExpired();
  }
});
