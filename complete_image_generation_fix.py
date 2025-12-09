#!/usr/bin/env python3
"""
Финальный скрипт для завершения исправлений генерации изображений:
1. Обновляет image-generation.js для вставки очереди в placeholder
2. Добавляет динамический расчёт цены в update-image-model-info.js
3. Обновляет отображение стоимости в шаблоне
"""

import re

print("🔧 Обновление системы генерации изображений...")

# 1. Обновляем image-generation.js
print("\n1️⃣ Обновление image-generation.js...")
with open('static/js/image-generation.js', 'r', encoding='utf-8') as f:
    img_gen_content = f.read()

# Заменяем место вставки очереди на placeholder
old_anchor = "const anchor = document.getElementById('image-model-cards');"
new_anchor = "const placeholder = document.getElementById('image-queue-placeholder');"

old_insert = """const host = (anchor && anchor.parentElement) || document.getElementById('gen-root') || document.body;
    const card = document.createElement('div');
    card.id = 'image-queue-card';
    card.className = 'card p-6 mt-6';"""

new_insert = """const host = placeholder || document.getElementById('gen-root') || document.body;
    const card = document.createElement('div');
    card.id = 'image-queue-card';
    card.className = 'card p-6';"""

old_append = """if (host && anchor && anchor.nextSibling) {
      host.insertBefore(card, anchor.nextSibling);
    } else {
      host.appendChild(card);
    }"""

new_append = """if (placeholder) {
      placeholder.appendChild(card);
    } else {
      host.appendChild(card);
    }"""

img_gen_content = img_gen_content.replace(old_anchor, new_anchor)
img_gen_content = img_gen_content.replace(old_insert, new_insert)
img_gen_content = img_gen_content.replace(old_append, new_append)

with open('static/js/image-generation.js', 'w', encoding='utf-8') as f:
    f.write(img_gen_content)

print("✅ image-generation.js обновлён")

# 2. Создаём скрипт для динамического расчёта цены
print("\n2️⃣ Создание скрипта динамического расчёта цены...")

price_calculator_script = """/**
 * Dynamic Price Calculator for Image Generation
 * Calculates total cost based on: base_cost × number_of_images
 */
(function() {
  'use strict';

  let baseCost = 10; // Default base cost

  function updateTotalCost() {
    try {
      const numberResults = document.getElementById('number-results');
      const currentModelCost = document.getElementById('current-model-cost');
      const totalCostDisplay = document.getElementById('total-cost-display');

      if (!numberResults || !currentModelCost) return;

      const quantity = parseInt(numberResults.value) || 1;
      const total = baseCost * quantity;

      // Update display
      if (currentModelCost) {
        currentModelCost.textContent = baseCost;
      }

      if (totalCostDisplay) {
        if (quantity > 1) {
          totalCostDisplay.innerHTML = `${baseCost} × ${quantity} = <strong>${total}</strong> TOK`;
        } else {
          totalCostDisplay.innerHTML = `<strong>${total}</strong> TOK`;
        }
      }

      // Update in model info section if exists
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
"""

with open('static/js/image-price-calculator.js', 'w', encoding='utf-8') as f:
    f.write(price_calculator_script)

print("✅ image-price-calculator.js создан")

# 3. Обновляем update-image-model-info.js для интеграции с калькулятором
print("\n3️⃣ Обновление update-image-model-info.js...")

with open('static/js/update-image-model-info.js', 'r', encoding='utf-8') as f:
    update_info_content = f.read()

# Добавляем вызов обновления базовой цены
if 'window.updateImageBaseCost' not in update_info_content:
    # Находим место где обновляется стоимость
    cost_update_pattern = r"(costEl\.textContent = `\$\{cost\} TOK`;)"
    cost_update_replacement = r"\1\n    // Update base cost for price calculator\n    if (typeof window.updateImageBaseCost === 'function') {\n      window.updateImageBaseCost(cost);\n    }"

    update_info_content = re.sub(cost_update_pattern, cost_update_replacement, update_info_content)

    with open('static/js/update-image-model-info.js', 'w', encoding='utf-8') as f:
        f.write(update_info_content)

    print("✅ update-image-model-info.js обновлён")
else:
    print("ℹ️  update-image-model-info.js уже содержит интеграцию")

print("\n✅ Все обновления завершены!")
print("\n📋 Итоговые изменения:")
print("1. ✅ Очередь генерации теперь вставляется в placeholder")
print("2. ✅ Создан калькулятор динамической цены")
print("3. ✅ Интеграция с системой обновления информации о модели")
print("\n🎯 Следующий шаг:")
print("- Добавить подключение image-price-calculator.js в шаблон new.html")
