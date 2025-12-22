/**
 * Aspect Ratio Quality Selector
 * Компонент для выбора соотношения сторон и качества с автозаполнением размеров
 */

class AspectRatioQualitySelector {
    constructor(options = {}) {
        this.modelType = options.modelType || 'image'; // 'image' или 'video'
        this.modelId = options.modelId;
        this.aspectRatioSelect = options.aspectRatioSelect; // элемент select для соотношений
        this.qualitySelect = options.qualitySelect; // элемент select для качества
        this.widthInput = options.widthInput; // input для ширины
        this.heightInput = options.heightInput; // input для высоты
        
        this.configs = {}; // Загруженные конфигурации
        this.currentAspectRatio = null;
        
        this.init();
    }
    
    async init() {
        if (!this.modelId) {
            console.warn('AspectRatioQualitySelector: model ID not provided');
            return;
        }
        
        // Загружаем конфигурации
        await this.loadConfigs();
        
        // Устанавливаем обработчики
        this.setupEventListeners();
        
        // Инициализируем селекторы
        this.populateAspectRatioSelect();
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
            
            console.log('Loaded aspect ratio configs:', this.configs);
        } catch (error) {
            console.error('Failed to load aspect ratio configs:', error);
        }
    }
    
    setupEventListeners() {
        if (this.aspectRatioSelect) {
            this.aspectRatioSelect.addEventListener('change', () => this.onAspectRatioChange());
        }
        
        if (this.qualitySelect) {
            this.qualitySelect.addEventListener('change', () => this.onQualityChange());
        }
    }
    
    populateAspectRatioSelect() {
        if (!this.aspectRatioSelect) return;
        
        // Очищаем текущие опции (кроме первой - placeholder)
        while (this.aspectRatioSelect.options.length > 1) {
            this.aspectRatioSelect.remove(1);
        }
        
        // Добавляем опции из конфигураций
        Object.keys(this.configs).forEach(ratio => {
            const option = document.createElement('option');
            option.value = ratio;
            option.textContent = ratio;
            this.aspectRatioSelect.appendChild(option);
        });
        
        // Если есть только одно соотношение, выбираем его автоматически
        if (Object.keys(this.configs).length === 1) {
            this.aspectRatioSelect.value = Object.keys(this.configs)[0];
            this.onAspectRatioChange();
        }
    }
    
    onAspectRatioChange() {
        const selectedRatio = this.aspectRatioSelect.value;
        this.currentAspectRatio = selectedRatio;
        
        // Обновляем селектор качества
        this.populateQualitySelect(selectedRatio);
    }
    
    populateQualitySelect(ratio) {
        if (!this.qualitySelect) return;
        
        // Очищаем текущие опции (кроме первой - placeholder)
        while (this.qualitySelect.options.length > 1) {
            this.qualitySelect.remove(1);
        }
        
        const qualities = this.configs[ratio] || [];
        
        // Добавляем опции качества
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
        
        // Если есть дефолтное или только одно качество, выбираем его
        if (qualities.length > 0) {
            const defaultQuality = qualities.find(q => q.is_default);
            if (defaultQuality) {
                this.qualitySelect.value = defaultQuality.quality;
            } else if (qualities.length === 1) {
                this.qualitySelect.value = qualities[0].quality;
            }
            this.onQualityChange();
        }
    }
    
    onQualityChange() {
        const selectedOption = this.qualitySelect.options[this.qualitySelect.selectedIndex];
        
        if (selectedOption && selectedOption.dataset.width && selectedOption.dataset.height) {
            // Заполняем поля width и height
            if (this.widthInput) {
                this.widthInput.value = selectedOption.dataset.width;
                
                // Триггерим событие change для обновления UI
                const event = new Event('change', { bubbles: true });
                this.widthInput.dispatchEvent(event);
            }
            
            if (this.heightInput) {
                this.heightInput.value = selectedOption.dataset.height;
                
                const event = new Event('change', { bubbles: true });
                this.heightInput.dispatchEvent(event);
            }
        }
    }
    
    /**
     * Обновляет конфигурации при смене модели
     */
    async updateModel(modelId) {
        this.modelId = modelId;
        await this.loadConfigs();
        this.populateAspectRatioSelect();
    }
    
    /**
     * Получает текущие выбранные размеры
     */
    getCurrentDimensions() {
        return {
            aspectRatio: this.currentAspectRatio,
            quality: this.qualitySelect ? this.qualitySelect.value : null,
            width: this.widthInput ? parseInt(this.widthInput.value) : null,
            height: this.heightInput ? parseInt(this.heightInput.value) : null
        };
    }
}

// Экспортируем для использования
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AspectRatioQualitySelector;
}
