#!/usr/bin/env python3
"""
Перемещение блока параметров:
1. Переместить сразу после кнопки генерации
2. Скрыть по умолчанию
3. Добавить правильные отступы
"""

import re
print("🔧 Перемещение блока параметров...")

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Находим и удаляем текущий блок параметров
params_start = '  <!-- Очередь генерации (placeholder для динамической вставки) -->'
params_end = '  </form>'

# Находим блок параметров

# Ищем блок от "Очередь генерации" до </form>
pattern = r'(  <!-- Очередь генерации \(placeholder для динамической вставки\) -->.*?)(  </form>)'
match = re.search(pattern, content, re.DOTALL)

if match:
    # Извлекаем блок параметров (всё между очередью и </form>)
    full_block = match.group(0)

    # Находим где начинается блок параметров (после placeholder очереди)
    queue_placeholder = '  <div id="image-queue-placeholder"></div>'

    # Извлекаем только блок параметров
    params_pattern = r'(<div class="card p-6 mt-6" id="image-params-section".*?{% include \'generate/reference_upload_compact\.html\' with target_id=\'image\' %}\s*</div>)'
    params_match = re.search(params_pattern, content, re.DOTALL)

    if params_match:
        params_block = params_match.group(1)

        # Удаляем старый блок параметров
        content = content.replace(params_block, '')

        # Добавляем hidden класс и убираем mt-6
        params_block_hidden = params_block.replace(
            '<div class="card p-6 mt-6" id="image-params-section"',
            '<div class="card p-6 mt-6 hidden" id="image-params-section"'
        )

        # Находим кнопку генерации и вставляем параметры после неё
        button_pattern = r'(          </button>\s*</div>\s*</div>)'
