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
        // Update available resolutions
        if (model.available_resolutions && model.available_resolutions.length > 0) {
            this.updateResolutionOptions(model.available_resolutions);
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
