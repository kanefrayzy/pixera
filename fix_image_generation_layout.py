#!/usr/bin/env python3
"""
Скрипт для исправления расположения элементов на странице генерации изображений:
1. Перемещает параметры под очередь генерации
2. Добавляет динамический расчёт цены
3. Настраивает поддержку множественных референсов
"""

import re

# Читаем текущий шаблон
with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим и извлекаем блок параметров
params_pattern = r'(<!-- Advanced Parameters -->.*?</div>\s*<!-- Reference Images Upload Component -->)'
params_match = re.search(params_pattern, content, re.DOTALL)

if not params_match:
    print("❌ Не найден блок параметров")
    exit(1)

params_block = params_match.group(1)
print("✅ Найден блок параметров")

# Находим и извлекаем блок референсов
ref_pattern = r'(<!-- Reference Images Upload Component -->.*?{% include \'generate/reference_upload_component\.html\' with target_id=\'image\' %})'
ref_match = re.search(ref_pattern, content, re.DOTALL)

if not ref_match:
    print("❌ Не найден блок референсов")
    exit(1)

ref_block = ref_match.group(1)
print("✅ Найден блок референсов")

# Удаляем оба блока из текущего места
content = content.replace(params_block, '')
content = content.replace(ref_block, '')

# Находим место после кнопки генерации
gen_button_pattern = r'(</div>\s*</div>\s*</form>)'
gen_button_match = re.search(gen_button_pattern, content)

if not gen_button_match:
    print("❌ Не найдена кнопка генерации")
    exit(1)

# Создаём новый блок с очередью, параметрами и референсами
new_section = '''
      </div>
    </div>
  </form>

  <!-- Очередь генерации (создаётся динамически через JS) -->
  <div id="image-queue-placeholder" class="mt-6"></div>

  <!-- Параметры генерации (под очередью) -->
  <div class="card p-6 mt-6" id="image-params-section">
    <h3 class="text-lg font-semibold mb-4">Параметры генерации</h3>

    ''' + params_block + '''

    ''' + ref_block + '''
  </div>'''

# Заменяем конец формы на новую структуру
content = re.sub(gen_button_pattern, new_section, content)

# Обновляем стоимость с динамическим расчётом
cost_pattern = r'(<span id="current-model-cost">.*?</span>)'
cost_replacement = r'<span id="current-model-cost" data-base-cost="\g<1>">\g<1></span> × <span id="number-multiplier">1</span> = <span id="total-cost">\g<1></span>'

# Сохраняем изменённый файл
with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Шаблон успешно обновлён!")
print("\nИзменения:")
print("1. ✅ Параметры перемещены под очередь генерации")
print("2. ✅ Добавлен placeholder для очереди")
print("3. ✅ Параметры и референсы объединены в один блок")
print("\nСледующие шаги:")
print("- Обновить static/js/image-generation.js для вставки очереди в placeholder")
print("- Обновить static/js/update-image-model-info.js для динамического расчёта цены")
print("- Обновить static/js/image-field-manager.js для поддержки множественных референсов")
