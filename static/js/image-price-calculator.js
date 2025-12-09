/**
 * Dynamic Price Calculator for Image Generation
 * Calculates total cost based on: base_cost × number_of_images
 */
(function() {
  'use strict';

  let baseCost = 10; // Default base cost

  function updateTotalCost() {
    try {
      const numberResults = document.getElementById('number-results');
      const quantity = parseInt(numberResults?.value) || 1;
      const total = baseCost * quantity;

      // 1. Update #current-model-cost (над промптом)
      const currentModelCost = document.getElementById('current-model-cost');
      if (currentModelCost) {
        if (quantity > 1) {
          currentModelCost.textContent = `${baseCost} × ${quantity} = ${total}`;
        } else {
          currentModelCost.textContent = baseCost;
        }
      }

      // 2. Update #total-cost-display (если есть)
      const totalCostDisplay = document.getElementById('total-cost-display');
      if (totalCostDisplay) {
        if (quantity > 1) {
          totalCostDisplay.innerHTML = `${baseCost} × ${quantity} = <strong>${total}</strong> TOK`;
        } else {
          totalCostDisplay.innerHTML = `<strong>${total}</strong> TOK`;
        }
      }

      // 3. Update #image-model-info-cost (в блоке информации о модели)
      const modelInfoCost = document.getElementById('image-model-info-cost');
      if (modelInfoCost) {
        if (quantity > 1) {
          modelInfoCost.textContent = `${baseCost} × ${quantity} = ${total} TOK`;
        } else {
          modelInfoCost.textContent = `${total} TOK`;
        }
      }
    } catch(e) {
      console.error('Error updating total cost:', e);
    }
  }

  // Update base cost when model changes
  window.updateImageBaseCost = function(cost) {
    baseCost = parseInt(cost) || 10;
    updateTotalCost();
  };

  // Listen for number_results changes
  document.addEventListener('DOMContentLoaded', function() {
    const numberResults = document.getElementById('number-results');
    if (numberResults) {
      numberResults.addEventListener('input', updateTotalCost);
      numberResults.addEventListener('change', updateTotalCost);
    }

    // Initial calculation
    updateTotalCost();
  });

  // Export for use by other scripts
  window.imageGenPriceCalculator = {
    updateTotalCost: updateTotalCost,
    setBaseCost: function(cost) {
      baseCost = parseInt(cost) || 10;
      updateTotalCost();
    }
  };
})();
