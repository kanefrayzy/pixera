/**
 * Moon Slider Handler
 * Универсальный обработчик для всех ползунков с луной
 * Автоматически инициализирует все .moon-slider элементы
 */

(function() {
  'use strict';

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMoonSliders);
  } else {
    initMoonSliders();
  }

  function initMoonSliders() {
    // Find all moon sliders
    const sliders = document.querySelectorAll('.moon-slider');

    if (sliders.length === 0) {
      console.log('[MoonSlider] No moon sliders found');
      return;
    }

    console.log(`[MoonSlider] Initializing ${sliders.length} slider(s)`);

    sliders.forEach(slider => {
      initSlider(slider);
    });
  }

  function initSlider(slider) {
    // Get associated value display element
    const valueId = slider.getAttribute('data-value-id');
    const valueDisplay = valueId ? document.getElementById(valueId) : null;

    if (!valueDisplay) {
      console.warn('[MoonSlider] No value display found for slider:', slider.id);
    }

    // Check if slider has labels (for Quality)
    const labelsAttr = slider.getAttribute('data-labels');
    const labels = labelsAttr ? JSON.parse(labelsAttr) : null;
    const hiddenInput = labels ? document.getElementById(slider.id + '-hidden') : null;

    // Quality value mapping
    const qualityValues = ['', 'low', 'medium', 'high', 'ultra'];

    // Track previous value for rotation calculation
    let previousValue = parseFloat(slider.value) || 0;
    let currentRotation = 0;

    // Update function
    function updateSlider() {
      const value = parseFloat(slider.value);
      const min = parseFloat(slider.min) || 0;
      const max = parseFloat(slider.max) || 100;

      // Calculate percentage for track fill
      const percentage = ((value - min) / (max - min)) * 100;
      slider.style.setProperty('--slider-value', percentage + '%');

      // Calculate rotation based on value change (moon rolls along the beam)
      const valueDelta = value - previousValue;
      const rotationDelta = valueDelta * 6; // 6 degrees per unit of movement
      currentRotation += rotationDelta;
      previousValue = value;

      // Apply rotation to create rolling effect
      // Note: We can't directly rotate ::-webkit-slider-thumb with JS,
      // so we use a CSS custom property
      slider.style.setProperty('--moon-rotation', `${currentRotation}deg`);

      // Update value display if exists
      if (valueDisplay) {
        if (labels) {
          // Use label instead of number
          const index = parseInt(value);
          valueDisplay.textContent = labels[index] || value;

          // Update hidden input with actual value
          if (hiddenInput && qualityValues[index] !== undefined) {
            hiddenInput.value = qualityValues[index];
          }
        } else {
          valueDisplay.textContent = value;
        }
      }

      console.log(`[MoonSlider] ${slider.id || 'slider'} updated to:`, value, `rotation: ${currentRotation}deg`);
    }

    // Listen for input events
    slider.addEventListener('input', updateSlider);

    // Listen for change events (for accessibility)
    slider.addEventListener('change', updateSlider);

    // Initialize on load
    updateSlider();

    console.log('[MoonSlider] Initialized:', slider.id || 'unnamed slider');
  }

  // Export for manual initialization if needed
  if (typeof window !== 'undefined') {
    window.initMoonSliders = initMoonSliders;
  }
})();
