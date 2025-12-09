/**
 * Image Model Info Display and Field Management
 * Показывает информацию о выбранной модели и управляет видимостью полей
 */

(function() {
  'use strict';

  // Ждем загрузки DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    const infoSection = document.getElementById('image-model-info-section');
    const cards = document.querySelectorAll('.image-model-card');

    if (!infoSection || !cards.length) return;

    // Слушаем клики по карточкам моделей
    cards.forEach(card => {
      card.addEventListener('click', function() {
        updateModelInfo(this);
      });
    });

    // Показываем информацию для выбранной модели при загрузке
    const selectedCard = document.querySelector('.image-model-card[data-selected="1"]');
    if (selectedCard) {
      updateModelInfo(selectedCard);
    }
  }

  function updateModelInfo(card) {
    const infoSection = document.getElementById('image-model-info-section');
    if (!infoSection) return;

    try {
      const config = JSON.parse(card.dataset.config || '{}');

      // Обновляем название и описание
      const nameEl = document.getElementById('image-model-info-name');
      const descEl = document.getElementById('image-model-info-description');
      const costEl = document.getElementById('image-model-info-cost');

      if (nameEl) nameEl.textContent = config.name || 'Модель';
      if (descEl) descEl.textContent = config.description || '';

      // Обновляем базовую стоимость в калькуляторе
      const tokenCost = config.token_cost || 10;
      if (window.imageGenPriceCalculator) {
        window.imageGenPriceCalculator.setBaseCost(tokenCost);
      } else if (window.updateImageBaseCost) {
        window.updateImageBaseCost(tokenCost);
      } else {
        // Fallback: обновляем все элементы цены вручную
        const currentModelCost = document.getElementById('current-model-cost');
        if (currentModelCost) currentModelCost.textContent = tokenCost;
        if (costEl) costEl.textContent = `${tokenCost} TOK`;
        const totalCostDisplay = document.getElementById('total-cost-display');
        if (totalCostDisplay) totalCostDisplay.innerHTML = `<strong>${tokenCost}</strong> TOK`;
      }

      // Обновляем список доступных параметров
      updateFeaturesList(config);

      // Показываем секцию
      infoSection.classList.remove('hidden');

    } catch (e) {
      console.error('Error updating image model info:', e);
    }
  }

  function updateFeaturesList(config) {
    const featuresList = document.getElementById('image-model-features-list');
    if (!featuresList) return;

    const features = [];
    const optionalFields = config.optional_fields || {};

    // Проверяем какие поля доступны
    if (optionalFields.resolution !== false) {
      features.push({ name: 'Разрешение', icon: 'monitor' });
    }
    if (optionalFields.steps !== false) {
      features.push({ name: 'Steps', icon: 'layers' });
    }
    if (optionalFields.cfg_scale !== false) {
      features.push({ name: 'CFG Scale', icon: 'sliders' });
    }
    if (optionalFields.scheduler !== false) {
      features.push({ name: 'Scheduler', icon: 'clock' });
    }
    if (optionalFields.seed !== false) {
      features.push({ name: 'Seed', icon: 'hash' });
    }
    if (optionalFields.negative_prompt !== false) {
      features.push({ name: 'Negative Prompt', icon: 'x-circle' });
    }
    if (optionalFields.number_results !== false) {
      features.push({ name: 'Количество', icon: 'copy' });
    }

    // Рендерим бейджи
    featuresList.innerHTML = features.map(f => `
      <span class="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-primary text-[10px] sm:text-xs font-medium">
        ${getIcon(f.icon)}
        ${f.name}
      </span>
    `).join('');
  }

  function getIcon(name) {
    const icons = {
      'monitor': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
      'layers': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg>',
      'sliders': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>',
      'clock': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
      'hash': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18"/></svg>',
      'x-circle': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
      'copy': '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>'
    };
    return icons[name] || '';
  }

})();
