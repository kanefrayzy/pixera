/**
 * Aspect Ratio Slider
 * Ползунок для выбора соотношения сторон в стиле сайта
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
        this.currentIndex = 0;

        this.init();
    }

    async init() {
        if (!this.modelId || !this.container) {
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

            this.configs = {};
            data.aspect_ratios.forEach(item => {
                this.configs[item.ratio] = item.qualities;
            });

            this.ratios = Object.keys(this.configs);

            // Находим индекс дефолтного соотношения
            const defaultRatio = data.aspect_ratios.find(ar => ar.qualities.some(q => q.is_default));
            if (defaultRatio) {
                this.currentIndex = this.ratios.indexOf(defaultRatio.ratio);
            }
        } catch (error) {
            // Silently handle error
        }
    }

    getRatioIcon(ratio) {
        const [w, h] = ratio.split(':').map(Number);
        const isPortrait = h > w;
        const isSquare = h === w;
        const isUltrawide = w / h > 2;

        if (isSquare) {
            return `<svg class="w-8 h-8" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>`;
        } else if (isPortrait) {
            return `<svg class="w-6 h-10" viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="3" width="10" height="18" rx="2"/></svg>`;
        } else if (isUltrawide) {
            return `<svg class="w-12 h-6" viewBox="0 0 24 24" fill="currentColor"><rect x="2" y="8" width="20" height="8" rx="2"/></svg>`;
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

        const currentRatio = this.ratios[this.currentIndex];

        this.container.innerHTML = `
            <div class="aspect-ratio-slider-wrapper">
                <!-- Заголовок с иконкой -->
                <div class="flex items-center justify-between mb-3">
                    <label class="text-sm font-medium text-[var(--text)]">
                        Соотношение сторон
                    </label>
                    <div class="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full shadow-lg min-h-[40px]">
                        <div class="text-white flex items-center justify-center w-12 h-10">
                            ${this.getRatioIcon(currentRatio)}
                        </div>
                        <span class="text-white font-bold text-sm whitespace-nowrap">${currentRatio}</span>
                    </div>
                </div>

                <!-- Ползунок -->
                <div class="relative px-2">
                    <input
                        type="range"
                        class="ar-slider w-full h-2 rounded-lg appearance-none cursor-pointer"
                        min="0"
                        max="${this.ratios.length - 1}"
                        value="${this.currentIndex}"
                        step="1"
                    />

                    <!-- Метки под ползунком -->
                    <div class="flex justify-between mt-2 px-0.5">
                        ${this.ratios.map((ratio, idx) => `
                            <button
                                type="button"
                                class="ar-label ${idx === this.currentIndex ? 'active' : ''}"
                                data-index="${idx}"
                                onclick="window.aspectRatioSliderInstance.jumpToIndex(${idx})">
                                ${ratio}
                            </button>
                        `).join('')}
                    </div>
                </div>
            </div>

            <style>
                .ar-slider {
                    background: linear-gradient(90deg,
                        #0f172a 0%,
                        #1e293b 25%,
                        #334155 50%,
                        #475569 75%,
                        #64748b 100%
                    );
                    outline: none;
                    position: relative;
                }

                .ar-slider::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    appearance: none;
                    width: 20px;
                    height: 20px;
                    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
                    cursor: pointer;
                    border-radius: 50%;
                    border: 3px solid #0f172a;
                    box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.3), 0 4px 12px rgba(6, 182, 212, 0.4);
                    transition: all 0.2s ease;
                }

                .ar-slider::-webkit-slider-thumb:hover {
                    transform: scale(1.15);
                    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.5), 0 6px 16px rgba(6, 182, 212, 0.6);
                }

                .ar-slider::-moz-range-thumb {
                    width: 20px;
                    height: 20px;
                    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
                    cursor: pointer;
                    border-radius: 50%;
                    border: 3px solid #0f172a;
                    box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.3), 0 4px 12px rgba(6, 182, 212, 0.4);
                    transition: all 0.2s ease;
                }

                .ar-slider::-moz-range-thumb:hover {
                    transform: scale(1.15);
                    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.5), 0 6px 16px rgba(6, 182, 212, 0.6);
                }

                .ar-label {
                    padding: 0.25rem 0.5rem;
                    font-size: 0.75rem;
                    color: var(--muted);
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 0.5rem;
                    cursor: pointer;
                    transition: all 0.2s;
                    flex: 1;
                    text-align: center;
                    min-width: 0;
                    max-width: 40px;
                }

                .ar-label:hover {
                    color: var(--text);
                    background: var(--bg-hover);
                    border-color: var(--bord);
                }

                .ar-label.active {
                    color: #06b6d4;
                    font-weight: 600;
                    background: rgba(6, 182, 212, 0.1);
                    border-color: #06b6d4;
                }
            </style>
        `;

        // Сохраняем ссылку на экземпляр
        window.aspectRatioSliderInstance = this;

        // Настраиваем обработчики после рендера
        this.setupEventListeners();

        // Автовыбор
        if (this.ratios[this.currentIndex]) {
            this.updateQualitySelect();
        }
    }

    setupEventListeners() {
        const slider = this.container.querySelector('.ar-slider');
        if (!slider) return;

        slider.addEventListener('input', (e) => {
            this.currentIndex = parseInt(e.target.value);
            this.updateUI();
            this.updateQualitySelect();
            this.onChange(this.ratios[this.currentIndex]);
        });
    }

    updateUI() {
        // Обновляем только UI элементы без полного перерендера
        const currentRatio = this.ratios[this.currentIndex];

        // Обновляем активные метки
        const labels = this.container.querySelectorAll('.ar-label');
        labels.forEach((label, idx) => {
            label.classList.toggle('active', idx === this.currentIndex);
        });

        // Обновляем иконку в бейдже
        const badgeContainer = this.container.querySelector('.flex.items-center.gap-2.px-3');
        if (badgeContainer) {
            const iconContainer = badgeContainer.querySelector('.text-white.flex.items-center');
            const textSpan = badgeContainer.querySelector('.font-bold');

            if (iconContainer) {
                iconContainer.innerHTML = this.getRatioIcon(currentRatio);
            }
            if (textSpan) {
                textSpan.textContent = currentRatio;
            }
        }
    }

    jumpToIndex(index) {
        this.currentIndex = index;
        this.render();
        this.setupEventListeners();
        this.onChange(this.ratios[this.currentIndex]);
    }

    updateQualitySelect() {
        if (!this.qualitySelect) return;

        const currentRatio = this.ratios[this.currentIndex];
        const qualities = this.configs[currentRatio] || [];

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

        // Показываем информацию о размерах
        const dimensionsInfo = document.getElementById('dimensions-info');
        const dimensionsDisplay = document.getElementById('dimensions-display');

        if (dimensionsInfo && dimensionsDisplay && width && height) {
            dimensionsDisplay.textContent = `${width} × ${height}`;
            dimensionsInfo.style.display = '';
        }
    }

    getCurrentRatio() {
        return this.ratios[this.currentIndex];
    }
}

window.AspectRatioSlider = AspectRatioSlider;
