/**
 * Aspect Ratio Slider
 * Слайдер для выбора соотношения сторон с иконкой и подписью
 */

class AspectRatioSlider {
    constructor(options = {}) {
        this.container = options.container; // контейнер для слайдера
        this.modelType = options.modelType || 'image';
        this.modelId = options.modelId;
        this.qualitySelect = options.qualitySelect; // связанный селектор качества
        this.widthInput = options.widthInput;
        this.heightInput = options.heightInput;
        this.onChange = options.onChange || (() => {});
        
        this.configs = {}; // Конфигурации моделей
        this.ratios = []; // Массив доступных соотношений
        this.currentIndex = 0;
        
        this.init();
    }
    
    async init() {
        if (!this.modelId || !this.container) {
            console.warn('AspectRatioSlider: container or model ID not provided');
            return;
        }
        
        await this.loadConfigs();
        this.render();
        this.setupEventListeners();
    }
    
    async loadConfigs() {
        try {
            const response = await fetch(`/generate/api/aspect-ratio-configs/${this.modelType}/${this.modelId}`);
            const data = await response.json();
            
            // Преобразуем в удобный формат
            this.configs = {};
            data.aspect_ratios.forEach(item => {
                this.configs[item.ratio] = item.qualities;
            });
            
            this.ratios = Object.keys(this.configs);
            
            // Находим индекс дефолтного соотношения или берем первое
            this.currentIndex = 0;
            const defaultRatio = data.aspect_ratios.find(ar => ar.qualities.some(q => q.is_default));
            if (defaultRatio) {
                this.currentIndex = this.ratios.indexOf(defaultRatio.ratio);
            }
            
            console.log('Loaded aspect ratio configs:', this.configs);
        } catch (error) {
            console.error('Failed to load aspect ratio configs:', error);
        }
    }
    
    render() {
        if (this.ratios.length === 0) {
            this.container.innerHTML = '<div class="text-sm text-gray-400">Нет доступных соотношений сторон</div>';
            return;
        }
        
        const currentRatio = this.ratios[this.currentIndex];
        
        this.container.innerHTML = `
            <div class="flex flex-col gap-3">
                <!-- Заголовок -->
                <div class="flex items-center justify-between">
                    <label class="text-sm font-medium text-gray-200">
                        Соотношение сторон
                    </label>
                    <div class="aspect-ratio-badge px-3 py-1.5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full text-white font-semibold text-sm shadow-lg">
                        ${currentRatio}
                    </div>
                </div>
                
                <!-- Слайдер с иконкой -->
                <div class="relative">
                    <!-- Иконка превью -->
                    <div class="absolute left-0 top-1/2 -translate-y-1/2 z-10">
                        <div class="aspect-ratio-icon-container w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg flex items-center justify-center">
                            <div class="aspect-ratio-icon ${this.getRatioIconClass(currentRatio)}">
                                ${this.getRatioIcon(currentRatio)}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Сам слайдер -->
                    <div class="pl-16">
                        <input 
                            type="range" 
                            class="aspect-ratio-slider w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer 
                                   focus:outline-none focus:ring-2 focus:ring-blue-500"
                            min="0" 
                            max="${this.ratios.length - 1}" 
                            value="${this.currentIndex}"
                            step="1"
                        />
                        
                        <!-- Метки под слайдером -->
                        <div class="flex justify-between mt-2 px-1">
                            ${this.ratios.map((ratio, idx) => `
                                <div class="text-xs ${idx === this.currentIndex ? 'text-blue-400 font-semibold' : 'text-gray-500'} transition-colors">
                                    ${ratio}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Обновляем связанные элементы
        this.updateRelatedElements();
    }
    
    getRatioIconClass(ratio) {
        // Классы для разных соотношений
        const orientationMap = {
            '1:1': 'square',
            '4:3': 'landscape',
            '3:2': 'landscape',
            '16:9': 'landscape',
            '21:9': 'ultrawide',
            '9:16': 'portrait',
            '4:5': 'portrait',
            '2:3': 'portrait',
        };
        
        return orientationMap[ratio] || 'square';
    }
    
    getRatioIcon(ratio) {
        // SVG иконки для разных ориентаций
        const [w, h] = ratio.split(':').map(Number);
        const isPortrait = h > w;
        const isSquare = h === w;
        const isUltrawide = w / h > 2;
        
        if (isSquare) {
            return `
                <svg class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <rect x="5" y="5" width="14" height="14" rx="2"/>
                </svg>
            `;
        } else if (isPortrait) {
            return `
                <svg class="w-5 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <rect x="7" y="3" width="10" height="18" rx="2"/>
                </svg>
            `;
        } else if (isUltrawide) {
            return `
                <svg class="w-8 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <rect x="2" y="8" width="20" height="8" rx="2"/>
                </svg>
            `;
        } else {
            return `
                <svg class="w-7 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <rect x="3" y="7" width="18" height="10" rx="2"/>
                </svg>
            `;
        }
    }
    
    setupEventListeners() {
        const slider = this.container.querySelector('.aspect-ratio-slider');
        if (!slider) return;
        
        slider.addEventListener('input', (e) => {
            this.currentIndex = parseInt(e.target.value);
            this.render();
            this.onChange(this.ratios[this.currentIndex]);
        });
    }
    
    updateRelatedElements() {
        const currentRatio = this.ratios[this.currentIndex];
        const qualities = this.configs[currentRatio] || [];
        
        // Обновляем селектор качества
        if (this.qualitySelect) {
            this.populateQualitySelect(qualities);
        }
    }
    
    populateQualitySelect(qualities) {
        if (!this.qualitySelect) return;
        
        // Очищаем опции
        this.qualitySelect.innerHTML = '<option value="">Выберите качество</option>';
        
        // Добавляем новые опции
        qualities.forEach(q => {
            const option = document.createElement('option');
            option.value = q.quality;
            option.textContent = `${q.quality_label} (${q.width}×${q.height})`;
            option.dataset.width = q.width;
            option.dataset.height = q.height;
            
            if (q.is_default) {
                option.setAttribute('selected', 'selected');
            }
            
            this.qualitySelect.appendChild(option);
        });
        
        // Автовыбор дефолта
        const defaultQuality = qualities.find(q => q.is_default);
        if (defaultQuality) {
            this.qualitySelect.value = defaultQuality.quality;
            this.updateDimensions(defaultQuality.width, defaultQuality.height);
        } else if (qualities.length === 1) {
            this.qualitySelect.value = qualities[0].quality;
            this.updateDimensions(qualities[0].width, qualities[0].height);
        }
        
        // Обработчик изменения качества
        this.qualitySelect.addEventListener('change', () => this.onQualityChange());
    }
    
    onQualityChange() {
        const selectedOption = this.qualitySelect.options[this.qualitySelect.selectedIndex];
        
        if (selectedOption && selectedOption.dataset.width && selectedOption.dataset.height) {
            this.updateDimensions(selectedOption.dataset.width, selectedOption.dataset.height);
        }
    }
    
    updateDimensions(width, height) {
        if (this.widthInput) {
            this.widthInput.value = width;
            this.widthInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        if (this.heightInput) {
            this.heightInput.value = height;
            this.heightInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
    
    getCurrentRatio() {
        return this.ratios[this.currentIndex];
    }
}

// Инициализация для глобального использования
window.AspectRatioSlider = AspectRatioSlider;
