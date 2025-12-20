/**
 * Image Field Manager
 * Manages visibility of form fields based on selected image model configuration
 */

class ImageFieldManager {
    constructor() {
        this.currentModel = null;
        this.fieldMap = {
            // Basic parameters
            'resolution': () => document.getElementById('resolution-selector'),
            // NOTE: aspect_ratio and custom_dimensions are managed separately in updateModelParameters
            // 'aspect_ratio': () => document.getElementById('aspect-ratio-selector'),
            // 'custom_dimensions': () => document.getElementById('custom-dimensions-field'),
            'steps': () => document.getElementById('steps-input'),
            'cfg_scale': () => document.getElementById('cfg-scale-input'),
            'scheduler': () => document.getElementById('scheduler-select'),
            'seed': () => document.getElementById('seed-input'),
            'negative_prompt': () => document.getElementById('negative-prompt'),
            'reference_images': () => document.querySelector('.reference-upload-compact[data-target="image"]'),
            'number_results': () => document.getElementById('number-results'),

            // UI elements
            'prompt': () => document.getElementById('prompt-input'),
            'auto_translate': () => document.getElementById('auto-translate-toggle'),
            'prompt_generator': () => document.getElementById('prompt-generator-button'),
        };
        this.targetPixels = 8294400; // Default: ~4K (3840x2160)
        this.initializeAspectRatioHandler();
    }

    /**
     * Initialize aspect ratio change handler
     */
    initializeAspectRatioHandler() {
        const aspectRatioSelect = document.getElementById('aspect-ratio-selector');
        if (aspectRatioSelect) {
            aspectRatioSelect.addEventListener('change', (e) => {
                const selectedRatio = e.target.value;
                if (selectedRatio && this.currentModel) {
                    this.calculateDimensions(selectedRatio);
                }
            });
        }
    }

    /**
     * Calculate width and height based on aspect ratio
     * @param {string} aspectRatioStr - Format: "16:9" or "16_9"
     */
    calculateDimensions(aspectRatioStr) {
        // Parse aspect ratio (handle both : and _ separators)
        const parts = aspectRatioStr.replace('_', ':').split(':').map(p => parseFloat(p));
        if (parts.length !== 2 || parts[0] <= 0 || parts[1] <= 0) {
            console.error('Invalid aspect ratio:', aspectRatioStr);
            return;
        }

        const [ratioW, ratioH] = parts;
        const ratio = ratioW / ratioH;
        const constraints = this.getModelConstraints();

        // Вычисляем размеры, стараясь максимально использовать доступное пространство
        // при сохранении соотношения сторон
        let width, height;

        if (ratio >= 1) {
            // Горизонтальное или квадратное
            width = constraints.maxWidth;
            height = Math.round(width / ratio);

            // Если высота превышает лимит, уменьшаем по высоте
            if (height > constraints.maxHeight) {
                height = constraints.maxHeight;
                width = Math.round(height * ratio);
            }
        } else {
            // Вертикальное
            height = constraints.maxHeight;
            width = Math.round(height * ratio);

            // Если ширина превышает лимит, уменьшаем по ширине
            if (width > constraints.maxWidth) {
                width = constraints.maxWidth;
                height = Math.round(width / ratio);
            }
        }

        // Убедимся, что не выходим за минимальные пределы
        width = Math.max(constraints.minWidth, Math.min(constraints.maxWidth, width));
        height = Math.max(constraints.minHeight, Math.min(constraints.maxHeight, height));

        // Update UI
        this.updateDimensionsUI(width, height);

        console.log(`Aspect ratio ${aspectRatioStr} → ${width}×${height} (${width * height} pixels)`);
    }

    /**
     * Clamp value between min and max
     */
    clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    /**
     * Get model constraints for dimensions
     */
    getModelConstraints() {
        if (!this.currentModel) {
            return { minWidth: 512, maxWidth: 4096, minHeight: 512, maxHeight: 4096 };
        }
        return {
            minWidth: this.currentModel.min_width || 512,
            maxWidth: this.currentModel.max_width || 4096,
            minHeight: this.currentModel.min_height || 512,
            maxHeight: this.currentModel.max_height || 4096
        };
    }

    /**
     * Update dimensions in UI
     */
    updateDimensionsUI(width, height) {
        const widthInput = document.getElementById('width-input');
        const heightInput = document.getElementById('height-input');
        const totalPixelsSpan = document.getElementById('total-pixels');

        if (widthInput) widthInput.value = width;
        if (heightInput) heightInput.value = height;
        if (totalPixelsSpan) {
            const total = width * height;
            totalPixelsSpan.textContent = total.toLocaleString('ru-RU');
        }
    }

    /**
     * Update field visibility based on model configuration
     * @param {Object} model - Model configuration object
     */
    updateFieldsForModel(model) {
        if (!model) {
            console.warn('ImageFieldManager: No model provided');
            return;
        }

        this.currentModel = model;
        const optionalFields = model.optional_fields || {};

        console.log('ImageFieldManager: Updating fields for model', model.name);
        console.log('Optional fields:', optionalFields);

        // Check if optional_fields is empty (no configuration set)
        const hasConfiguration = Object.keys(optionalFields).length > 0;

        if (!hasConfiguration) {
            // No configuration - hide all fields except always-visible UI elements
            console.log('ImageFieldManager: No optional_fields configuration - hiding all fields');
            this.hideParametersSection();
            Object.keys(this.fieldMap).forEach(fieldName => {
                const element = this.fieldMap[fieldName]();
                if (element) {
                    element.style.display = 'none';
                    const container = element.closest('.field-container');
                    if (container) {
                        container.style.display = 'none';
                    }
                }
            });
            // Show always-visible UI elements
            this.showAlwaysVisibleFields();
            return;
        }

        // Show the parameters section
        this.showParametersSection();

        // Update each field's visibility based on configuration
        Object.keys(this.fieldMap).forEach(fieldName => {
            const isEnabled = optionalFields[fieldName] === true;
            const element = this.fieldMap[fieldName]();

            if (element) {
                // Show or hide the field
                element.style.display = isEnabled ? '' : 'none';

                // Also update parent container if it has a specific class
                const container = element.closest('.field-container');
                if (container) {
                    container.style.display = isEnabled ? '' : 'none';
                }

                console.log(`Field "${fieldName}": ${isEnabled ? 'visible' : 'hidden'}`);
            } else {
                console.warn(`Field element not found for: ${fieldName}`);
            }
        });

        // Always show certain UI elements regardless of configuration
        this.showAlwaysVisibleFields();

        // Update model-specific parameters
        this.updateModelParameters(model);
    }

    /**
     * Show the parameters section
     */
    showParametersSection() {
        const paramsSection = document.getElementById('image-params-section');
        if (paramsSection) {
            paramsSection.classList.remove('hidden');
            console.log('ImageFieldManager: Parameters section shown');
        }
    }

    /**
     * Hide the parameters section
     */
    hideParametersSection() {
        const paramsSection = document.getElementById('image-params-section');
        if (paramsSection) {
            paramsSection.classList.add('hidden');
            console.log('ImageFieldManager: Parameters section hidden');
        }
    }

    /**
     * Show always-visible UI elements (prompt generator, etc.)
     */
    showAlwaysVisibleFields() {
        // Prompt generator should always be visible
        const promptGenerator = document.getElementById('prompt-generator-button');
        if (promptGenerator) {
            promptGenerator.style.display = '';
            const container = promptGenerator.closest('.field-container');
            if (container) {
                container.style.display = '';
            }
            console.log('ImageFieldManager: Showing always-visible: prompt_generator');
        }
    }

    /**
     * Update model-specific parameters (resolutions, limits, etc.)
     * @param {Object} model - Model configuration object
     */
    updateModelParameters(model) {
        // Update available aspect ratios (NEW!)
        if (model.available_aspect_ratios && model.available_aspect_ratios.length > 0) {
            console.log('Model has aspect ratios, showing aspect ratio selector');
            this.updateAspectRatioOptions(model.available_aspect_ratios);
            // Hide old resolution selector, show aspect ratio
            const resField = document.getElementById('resolution-field');
            const aspectField = document.getElementById('aspect-ratio-field');
            const customDimField = document.getElementById('custom-dimensions-field');
            if (resField) {
                resField.style.display = 'none';
                const container = resField.closest('.field-container');
                if (container) container.style.display = 'none';
            }
            if (aspectField) {
                aspectField.style.display = '';
                const container = aspectField.closest('.field-container');
                if (container) container.style.display = '';
            }
            if (customDimField) {
                customDimField.style.display = '';
                const container = customDimField.closest('.field-container');
                if (container) container.style.display = '';
            }
        } else {
            console.log('Model has NO aspect ratios, using old resolution selector');
            // No aspect ratios configured - use old resolution selector
            const resField = document.getElementById('resolution-field');
            const aspectField = document.getElementById('aspect-ratio-field');
            const customDimField = document.getElementById('custom-dimensions-field');
            if (resField && model.available_resolutions && model.available_resolutions.length > 0) {
                resField.style.display = '';
                const container = resField.closest('.field-container');
                if (container) container.style.display = '';
                this.updateResolutionOptions(model.available_resolutions);
            }
            if (aspectField) {
                aspectField.style.display = 'none';
                const container = aspectField.closest('.field-container');
                if (container) container.style.display = 'none';
            }
            if (customDimField) {
                customDimField.style.display = 'none';
                const container = customDimField.closest('.field-container');
                if (container) container.style.display = 'none';
            }
        }

        // Update steps limits
        if (model.supports_steps) {
            this.updateStepsLimits(model.min_steps, model.max_steps, model.default_steps);
        }

        // Update CFG scale limits
        if (model.supports_cfg_scale) {
            this.updateCfgScaleLimits(model.min_cfg_scale, model.max_cfg_scale, model.default_cfg_scale);
        }

        // Update reference images support
        if (model.supports_reference_images) {
            this.updateReferenceImagesSupport(model.max_reference_images);
        }

        // Update number of results limit
        if (model.supports_multiple_results) {
            this.updateNumberResultsLimit(model.max_number_results);
        }
    }

    /**
     * Update available aspect ratio options
     * @param {Array} aspectRatios - Array of aspect ratios like ["1:1", "16:9", "4:3"]
     */
    updateAspectRatioOptions(aspectRatios) {
        const aspectRatioSelect = document.getElementById('aspect-ratio-selector');
        if (!aspectRatioSelect) return;

        // Clear existing options except first (placeholder)
        aspectRatioSelect.innerHTML = '<option value="" disabled selected>Выберите соотношение сторон</option>';

        // Group labels
        const groups = {
            square: 'Квадратные',
            classic: 'Классические',
            modern: 'Современные',
            cinema: 'Киноформаты',
            ultrawide: 'Ультраширокие',
            vertical: 'Вертикальные',
            photo: 'Фотографические'
        };

        // Categorize aspect ratios
        const categorized = {
            square: ['1:1'],
            classic: ['4:3', '3:2', '5:4'],
            modern: ['16:9', '16:10'],
            cinema: ['21:9', '2.35:1', '2.39:1', '1.85:1'],
            ultrawide: ['32:9', '18:9'],
            vertical: ['9:16', '2:3', '3:4', '9:19.5'],
            photo: ['3:2', '2:3', '4:5', '5:4']
        };

        // Add options grouped
        const addedRatios = new Set();
        Object.entries(categorized).forEach(([groupKey, ratios]) => {
            const matchingRatios = aspectRatios.filter(r => {
                const normalized = r.replace('_', ':');
                return ratios.some(target => {
                    // Handle both "2.35:1" and "2_35_1" formats
                    const targetNorm = target.replace('.', '_').replace(':', '_');
                    const rNorm = normalized.replace('.', '_').replace(':', '_');
                    return targetNorm === rNorm || target === normalized;
                }) && !addedRatios.has(r);
            });

            if (matchingRatios.length > 0) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = groups[groupKey];
                matchingRatios.forEach(ratio => {
                    const option = document.createElement('option');
                    option.value = ratio;
                    const display = ratio.replace('_', ':');
                    option.textContent = display;
                    optgroup.appendChild(option);
                    addedRatios.add(ratio);
                });
                aspectRatioSelect.appendChild(optgroup);
            }
        });

        // Add ungrouped ratios
        const ungrouped = aspectRatios.filter(r => !addedRatios.has(r));
        if (ungrouped.length > 0) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = 'Другие';
            ungrouped.forEach(ratio => {
                const option = document.createElement('option');
                option.value = ratio;
                const display = ratio.replace('_', ':');
                option.textContent = display;
                optgroup.appendChild(option);
            });
            aspectRatioSelect.appendChild(optgroup);
        }

        console.log('Updated aspect ratio options:', aspectRatios);

        // Auto-select first ratio and calculate dimensions
        if (aspectRatios.length > 0) {
            aspectRatioSelect.value = aspectRatios[0];
            this.calculateDimensions(aspectRatios[0]);
        }
    }

    /**
     * Update available resolution options
     * @param {Array} resolutions - Array of available resolutions
     */
    updateResolutionOptions(resolutions) {
        const resolutionSelect = document.getElementById('resolution-selector');
        if (!resolutionSelect) return;

        // Clear existing options
        resolutionSelect.innerHTML = '';

        // Add new options
        resolutions.forEach(resolution => {
            const option = document.createElement('option');
            option.value = resolution;
            option.textContent = resolution;
            resolutionSelect.appendChild(option);
        });

        console.log('Updated resolution options:', resolutions);
    }

    /**
     * Update steps input limits
     */
    updateStepsLimits(min, max, defaultValue) {
        const stepsInput = document.getElementById('steps-input');
        if (!stepsInput) return;

        stepsInput.min = min || 1;
        stepsInput.max = max || 50;
        stepsInput.value = defaultValue || 20;

        console.log(`Updated steps limits: ${min}-${max}, default: ${defaultValue}`);
    }

    /**
     * Update CFG scale input limits
     */
    updateCfgScaleLimits(min, max, defaultValue) {
        const cfgInput = document.getElementById('cfg-scale-input');
        if (!cfgInput) return;

        cfgInput.min = min || 1.0;
        cfgInput.max = max || 20.0;
        cfgInput.value = defaultValue || 7.0;
        cfgInput.step = 0.1;

        console.log(`Updated CFG scale limits: ${min}-${max}, default: ${defaultValue}`);
    }

    /**
     * Update reference images support
     */
    updateReferenceImagesSupport(maxImages) {
        const refSection = document.querySelector('.reference-upload-compact[data-target="image"]');
        if (!refSection) {
            console.warn('Reference upload component not found');
            return;
        }

        // Update max images using the component's API
        if (typeof refSection.updateMaxRefs === 'function') {
            refSection.updateMaxRefs(maxImages || 0);
            console.log(`Updated reference images max: ${maxImages}`);
        } else {
            console.warn('updateMaxRefs function not available on reference component');
        }
    }

    /**
     * Update number of results limit
     */
    updateNumberResultsLimit(maxResults) {
        const resultsInput = document.getElementById('number-results');
        if (!resultsInput) return;

        resultsInput.max = maxResults || 4;
        if (parseInt(resultsInput.value) > maxResults) {
            resultsInput.value = maxResults;
        }

        console.log(`Updated number results limit: ${maxResults}`);
    }

    /**
     * Reset all fields to default visibility
     */
    resetFields() {
        Object.keys(this.fieldMap).forEach(fieldName => {
            const element = this.fieldMap[fieldName]();
            if (element) {
                element.style.display = '';
                const container = element.closest('.field-container');
                if (container) {
                    container.style.display = '';
                }
            }
        });

        // Hide parameters section
        this.hideParametersSection();

        this.currentModel = null;
        console.log('ImageFieldManager: Fields reset to default');
    }

    /**
     * Get current model
     */
    getCurrentModel() {
        return this.currentModel;
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImageFieldManager;
}

// Make available globally in browser
if (typeof window !== 'undefined') {
    window.ImageFieldManager = ImageFieldManager;
}
