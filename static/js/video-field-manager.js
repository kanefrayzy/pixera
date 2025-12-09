/**
 * Video Field Manager
 * Manages dynamic visibility of form fields based on selected video model configuration
 */

class VideoFieldManager {
  constructor() {
    this.currentModel = null;

    // Map field names from optional_fields to DOM elements
    // NOTE: 'duration' is NOT managed here - it's controlled by updateDurationLimit() in video-generation.js
    // which has special logic to hide the section when only one duration is available
    this.fieldMap = {
      // Basic fields (duration excluded - managed separately)
      'resolution': () => document.querySelector('[for="video-resolution"]')?.closest('.space-y-1'),
      'camera_movement': () => document.querySelector('[for="video-camera"]')?.closest('.space-y-1'),
      'seed': () => document.querySelector('[for="video-seed"]')?.closest('.space-y-1'),
      'number_videos': () => document.getElementById('video-quantity-container'),

      // I2V fields (source_image управляется режимом I2V/T2V, не optional_fields)
      'motion_strength': () => document.getElementById('motion-options')?.closest('.md\\:col-span-2'),
      'audio_inputs': () => document.querySelector('[for="i2v-audio-url"]')?.closest('.mt-3'),

      // Mode and prompt fields
      'generation_mode': () => document.getElementById('video-mode-block'),
      'prompt': () => document.querySelector('[for="video-prompt"]')?.closest('div'),
      'auto_translate': () => document.getElementById('auto-translate-toggle')?.closest('.inline-flex'),

      // Advanced fields
      'aspect_ratio': () => document.querySelector('.aspect-ratio-btn')?.closest('div'),
      'prompt_generator': () => document.getElementById('pg-video'),

      // Advanced parameters (new)
      'fps': () => document.getElementById('fps-param'),
      'guidance_scale': () => document.getElementById('guidance-scale-param'),
      'inference_steps': () => document.getElementById('inference-steps-param'),
      'quality': () => document.getElementById('quality-param'),
      'style': () => document.getElementById('style-param'),
      'output_format': () => document.getElementById('output-format-param'),
      'negative_prompt': () => document.getElementById('negative-prompt-param')
    };
  }

  /**
   * Update field visibility based on model's optional_fields configuration
   */
  updateFieldsForModel(model) {
    if (!model) {
      console.warn('[VideoFieldManager] No model provided');
      return;
    }

    this.currentModel = model;

    // Get optional_fields configuration from model
    const optionalFields = model.optional_fields || {};

    console.log('[VideoFieldManager] Model:', model.name);
    console.log('[VideoFieldManager] Optional fields config:', optionalFields);

    // Fields that must always remain visible in UI (mode toggle, prompt, auto-translate)
    const alwaysVisible = ['generation_mode', 'prompt', 'auto_translate'];

    // Check if optional_fields is empty (no configuration set)
    const hasConfiguration = Object.keys(optionalFields).length > 0;

    if (!hasConfiguration) {
      // No configuration - hide only optional blocks, but keep core controls visible
      console.log('[VideoFieldManager] No optional_fields configuration - hiding optional fields only');
      this.hideAllFields();
      this.showAlwaysVisibleFields();
      return;
    }

    // Show/hide ALL managed fields based on configuration,
    // but never hide core UI controls (mode, prompt, auto-translate)
    Object.keys(this.fieldMap).forEach(fieldName => {
      const element = this.fieldMap[fieldName] && this.fieldMap[fieldName]();
      if (!element) return;

      // Core controls are always visible regardless of optional_fields
      if (alwaysVisible.includes(fieldName)) {
        element.style.display = '';
        console.log(`[VideoFieldManager] Always-visible field: ${fieldName}`);
        return;
      }

      const isEnabled = optionalFields[fieldName] === true;

      if (isEnabled) {
        element.style.display = '';
        console.log(`[VideoFieldManager] Showing field: ${fieldName}`);
      } else {
        element.style.display = 'none';
        console.log(`[VideoFieldManager] Hiding field: ${fieldName}`);
      }
    });

    // Always show certain UI elements regardless of configuration
    this.showAlwaysVisibleFields();

    // Special handling for I2V fields container
    const i2vFields = document.getElementById('i2v-fields');
    if (i2vFields) {
      // Show I2V container if motion_strength is enabled
      if (optionalFields.motion_strength) {
        i2vFields.style.display = '';
      } else {
        i2vFields.style.display = 'none';
      }
    }

    // Special handling for advanced params section
    const advancedParamsSection = document.getElementById('advanced-params-section');
    if (advancedParamsSection) {
      // Show section if any advanced param is enabled
      const advancedParams = ['fps', 'guidance_scale', 'inference_steps', 'quality', 'style', 'output_format', 'negative_prompt'];
      const hasAnyAdvancedParam = advancedParams.some(param => optionalFields[param] === true);

      if (hasAnyAdvancedParam) {
        advancedParamsSection.style.display = '';
        console.log('[VideoFieldManager] Showing advanced params section');
      } else {
        advancedParamsSection.style.display = 'none';
        console.log('[VideoFieldManager] Hiding advanced params section');
      }
    }
  }

  /**
   * Hide all managed fields
   */
  hideAllFields() {
    // Core controls that must not be force-hidden
    const alwaysVisible = ['generation_mode', 'prompt', 'auto_translate'];

    Object.keys(this.fieldMap).forEach(fieldName => {
      if (alwaysVisible.includes(fieldName)) {
        return; // keep core controls visible
      }
      const getter = this.fieldMap[fieldName];
      const element = getter && getter();
      if (element) {
        element.style.display = 'none';
      }
    });

    // Also hide I2V container
    const i2vFields = document.getElementById('i2v-fields');
    if (i2vFields) {
      i2vFields.style.display = 'none';
    }
  }

  /**
   * Show always-visible UI elements (prompt generator, etc.)
   */
  showAlwaysVisibleFields() {
    // Prompt generator should always be visible
    const promptGenerator = document.getElementById('pg-video');
    if (promptGenerator) {
      promptGenerator.style.display = '';
      console.log('[VideoFieldManager] Showing always-visible: prompt_generator');
    }

    // Video mode toggle ("Фото/Видео" / "Текст/Видео") must always be visible
    const modeBlockGetter = this.fieldMap['generation_mode'];
    const modeBlock = modeBlockGetter && modeBlockGetter();
    if (modeBlock) {
      modeBlock.style.display = '';
      console.log('[VideoFieldManager] Showing always-visible: generation_mode');
    }

    // Video prompt label/field must always be visible
    const promptGetter = this.fieldMap['prompt'];
    const promptBlock = promptGetter && promptGetter();
    if (promptBlock) {
      promptBlock.style.display = '';
      console.log('[VideoFieldManager] Showing always-visible: prompt');
    }

    // Auto-translate toggle must always be visible
    const autoGetter = this.fieldMap['auto_translate'];
    const autoBlock = autoGetter && autoGetter();
    if (autoBlock) {
      autoBlock.style.display = '';
      console.log('[VideoFieldManager] Showing always-visible: auto_translate');
    }
  }

  /**
   * Show all fields (fallback for debugging)
   */
  showAllFields() {
    Object.keys(this.fieldMap).forEach(fieldName => {
      const element = this.fieldMap[fieldName]();
      if (element) {
        element.style.display = '';
      }
    });
  }
}

// Export for use in video-generation.js
if (typeof window !== 'undefined') {
  window.VideoFieldManager = VideoFieldManager;
}
