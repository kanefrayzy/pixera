/**
 * Aspect Ratio Slider
 * Простой и понятный селектор соотношения сторон
 */

class AspectRatioSlider {
    constructor(options = {}) {
        this.container = options.container;
        this.modelType = options.modelType || 'image';
        this.modelId = options.modelId;
        this.qualitySelect = options.qualitySelect;
        this.widthInput = options.widthInput;
        this.heightInput = options.heightInput;
        this.onChange = options.onChange || (() => {});
        
        this.configs = {};
        this.ratios = [];
        this.currentRatio = null;
        
        this.init();
    }
    
    async init() {
        if (!this.modelId || !this.container) {
            console.warn('AspectRatioSlider: container or model ID not provided');
            return;
        }
        
        await this.loadConfigs();
        this.render();
    }
    
    async loadConfigs() {
        try {
            const response = await fetch(`/generate/api/aspect-ratio-configs/${this.modelType}/${this.modelId}`);
            const data = await response.json();
            
            this.configs = {};
            data.aspect_ratios.forEach(item => {
                this.configs[item.ratio] = item.qualities;
            });
            
            this.ratios = Object.keys(this.configs);
            
            // Находим дефолт или берем первый
            const defaultRatio = data.aspect_ratios.find(ar => ar.qualities.some(q => q.is_default));
            this.currentRatio = defaultRatio ? defaultRatio.ratio : this.ratios[0];
            
            console.log('Loaded aspect ratio configs:', this.configs);
        } catch (error) {
            console.error('Failed to load aspect ratio configs:', error);
        }
    }
    
    getRatioIcon(ratio) {
        const [w, h] = ratio.split(':').map(Number);
        const isPortrait = h > w;
        const isSquare = h === w;
        
        if (isSquare) {
            return `<svg class="w-8 h-8" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>`;
        } else if (isPortrait) {
            return `<svg class="w-6 h-10" viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="3" width="10" height="18" rx="2"/></svg>`;
        } else {
            return `<svg class="w-10 h-6" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="7" width="18" height="10" rx="2"/></svg>`;
        }
    }
    
    render() {
        if (this.ratios.length === 0) {
            this.container.innerHTML = `
                <div class="text-sm text-gray-400">Нет доступных соотношений сторон для этой модели</div>
            `;
            return;
        }
        
        // Рендерим кнопки-карточки для каждого соотношения
        this.container.innerHTML = `
            <div class="aspect-ratio-selector">
                <label class="block text-sm font-medium mb-3 text-[var(--text)]">
                    Соотношение сторон
                </label>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                    ${this.ratios.map(ratio => `
                        <button type="button" 
                                class="aspect-ratio-btn ${ratio === this.currentRatio ? 'active' : ''}" 
                                data-ratio="${ratio}"
                                onclick="window.aspectRatioSliderInstance.selectRatio('${ratio}')">
                            <div class="flex flex-col items-center gap-2">
                                <div class="text-primary">
                                    ${this.getRatioIcon(ratio)}
                                </div>
                                <span class="font-semibold text-sm">${ratio}</span>
                            </div>
                        </button>
                    `).join('')}
                </div>
            </div>
            
            <style>
                .aspect-ratio-btn {
                    padding: 1rem;
                    background: var(--bg-card);
                    border: 2px solid var(--bord);
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                    color: var(--text);
                }
                
                .aspect-ratio-btn:hover {
                    border-color: var(--primary);
                    background: var(--bg-hover);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
                }
                
                .aspect-ratio-btn.active {
                    border-color: var(--primary);
                    background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
                    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
                }
            </style>
        `;
        
        // Сохраняем ссылку на экземпляр
        window.aspectRatioSliderInstance = this;
        
        // Автовыбор первого соотношения
        if (this.currentRatio) {
            this.updateQualitySelect();
        }
    }
    
    selectRatio(ratio) {
        this.currentRatio = ratio;
        
        // Обновляем активную кнопку
        this.container.querySelectorAll('.aspect-ratio-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.ratio === ratio);
        });
        
        this.updateQualitySelect();
        this.onChange(ratio);
    }
    
    updateQualitySelect() {
        if (!this.qualitySelect) return;
        
        const qualities = this.configs[this.currentRatio] || [];
        
        this.qualitySelect.innerHTML = '<option value="">Выберите качество</option>';
        
        qualities.forEach(q => {
            const option = document.createElement('option');
            option.value = q.quality;
            option.textContent = `${q.quality_label} (${q.width}×${q.height})`;
            option.dataset.width = q.width;
            option.dataset.height = q.height;
            
            if (q.is_default) {
                option.selected = true;
            }
            
            this.qualitySelect.appendChild(option);
        });
        
        // Автовыбор и заполнение размеров
        const defaultQuality = qualities.find(q => q.is_default);
        if (defaultQuality) {
            this.updateDimensions(defaultQuality.width, defaultQuality.height);
        } else if (qualities.length === 1) {
            this.updateDimensions(qualities[0].width, qualities[0].height);
        }
        
        // Обработчик изменения качества
        this.qualitySelect.removeEventListener('change', this.boundQualityChange);
        this.boundQualityChange = () => this.onQualityChange();
        this.qualitySelect.addEventListener('change', this.boundQualityChange);
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
        return this.currentRatio;
    }
}

