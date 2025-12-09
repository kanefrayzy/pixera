/**
 * Video Quantity Handler
 * Manages the video quantity slider and updates display
 */

(function() {
  'use strict';

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVideoQuantityHandler);
  } else {
    initVideoQuantityHandler();
  }

  function initVideoQuantityHandler() {
    const slider = document.getElementById('video-quantity');
    const valueDisplay = document.getElementById('video-quantity-value');

    if (!slider || !valueDisplay) {
      console.warn('[VideoQuantityHandler] Slider or value display not found');
      return;
    }

    // Update display when slider changes
    slider.addEventListener('input', function() {
      const value = this.value;
      valueDisplay.textContent = value;

      // Update slider track fill (for webkit browsers)
      const percentage = ((value - this.min) / (this.max - this.min)) * 100;
      this.style.setProperty('--value', percentage + '%');

      console.log('[VideoQuantityHandler] Quantity changed to:', value);
    });

    // Initialize slider track fill
    const initialValue = slider.value;
    const initialPercentage = ((initialValue - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.setProperty('--value', initialPercentage + '%');

    console.log('[VideoQuantityHandler] Initialized with value:', initialValue);
  }
})();
