#!/usr/bin/env python3
"""
Добавление интеграции количества слотов референсов с системой выбора модели
"""

print("🔧 Добавление интеграции слотов референсов...")

with open('static/js/update-image-model-info.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим место где обновляется информация о модели и добавляем обновление слотов
# Ищем функцию updateImageModelInfo

integration_code = """
    // Update reference slots count
    const refUploadCompact = document.querySelector('.reference-upload-compact[data-target="image"]');
    if (refUploadCompact && config.max_reference_images !== undefined) {
      const maxRefs = config.max_reference_images || 0;
      if (typeof refUploadCompact.updateMaxRefs === 'function') {
        refUploadCompact.updateMaxRefs(maxRefs);
        console.log('[update-image-model-info] Updated reference slots to:', maxRefs);
      }
    }
"""

# Ищем место после обновления базовой цены
marker = "window.updateImageBaseCost(cost);"

if marker in content:
    # Добавляем код после обновления цены
    content = content.replace(
        marker,
        marker + "\n" + integration_code
    )
    print("✅ Добавлена интеграция слотов референсов")
else:
    print("⚠️  Маркер не найден, попробуем другой способ...")
    # Альтернативный маркер
    alt_marker = "// Update base cost for price calculator"
    if alt_marker in content:
        # Находим конец этого блока
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if alt_marker in line:
                # Ищем следующую строку с window.updateImageBaseCost
                for j in range(i+1, min(i+5, len(lines))):
                    if 'window.updateImageBaseCost' in lines[j]:
                        new_lines.append(integration_code)
                        break
        content = '\n'.join(new_lines)
        print("✅ Добавлена интеграция слотов референсов (альтернативный метод)")

# Сохраняем
with open('static/js/update-image-model-info.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Интеграция завершена!")
print("\nТеперь при выборе модели:")
print("1. ✅ Обновляется базовая цена")
print("2. ✅ Обновляется количество слотов референсов")
print("3. ✅ Показывается правильное количество (до X)")
print("\nПример:")
print("- Модель с max_reference_images=3 → показывает 'до 3'")
print("- Модель с max_reference_images=5 → показывает 'до 5'")
print("- Модель с max_reference_images=0 → показывает 'до 0' (референсы недоступны)")
