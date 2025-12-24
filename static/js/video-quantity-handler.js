/**
 * Video Quantity Handler
 * Manages the video quantity slider and updates display
 */

(function() {
  'use strict';

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVideoQuantityHandler);
  } else {
    initVideoQuantityHandler();
  }

  function initVideoQuantityHandler() {
    var slider = document.getElementById('video-quantity');
    var valueDisplay = document.getElementById('video-quantity-value');
    if (!slider || !valueDisplay) return;

    slider.addEventListener('input', function() {
      var value = this.value;
      valueDisplay.textContent = value;
      var percentage = ((value - this.min) / (this.max - this.min)) * 100;
      this.style.setProperty('--value', percentage + '%');
    });

    var initialValue = slider.value;
    var initialPercentage = ((initialValue - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.setProperty('--value', initialPercentage + '%');
  }
})();
