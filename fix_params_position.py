#!/usr/bin/env python3
"""
Исправление позиции блока параметров - перемещение после информации о модели
"""

print("🔧 Исправление позиции блока параметров...")

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Находим и вырезаем блок параметров
params_start = '<div class="card p-6 mt-6 hidden" id="image-params-section">'
params_end_marker = '{% include \'generate/reference_upload_compact.html\' with target_id=\'image\' %}'

# Ищем начало блока
start_idx = content.find(params_start)
if start_idx == -1:
    print("❌ Блок параметров не найден!")
    exit(1)

print(f"✅ Блок параметров найден на позиции {start_idx}")

# Ищем конец блока (после include референсов + закрывающий div)
end_search_start = content.find(params_end_marker, start_idx)
if end_search_start == -1:
    print("❌ Конец блока параметров не найден!")
    exit(1)

# Находим закрывающий </div> после include
end_idx = content.find('</div>', end_search_start)
if end_idx == -1:
    print("❌ Закрывающий тег не найден!")
    exit(1)

end_idx += len('</div>')

# Вырезаем весь блок
params_block = content[start_idx:end_idx]
print(f"✅ Блок параметров вырезан (длина: {len(params_block)} символов)")

# Удаляем блок из текущего места
content = content[:start_idx] + content[end_idx:]

# 2. Находим место после блока информации о модели
# Ищем закрывающий тег блока image-model-info-section
model_info_end = '</div>\n      </div>'

# Ищем последнее вхождение этого паттерна в блоке image-model-info-section
model_info_start = content.find('id="image-model-info-section"')
if model_info_start == -1:
    print("❌ Блок информации о модели не найден!")
    exit(1)

# Ищем закрытие блока после начала
search_from = model_info_start
found_closes = []
while True:
    close_pos = content.find(model_info_end, search_from)
    if close_pos == -1:
        break
    found_closes.append(close_pos)
    search_from = close_pos + 1

if not found_closes:
    print("❌ Закрытие блока информации о модели не найдено!")
    exit(1)

# Берём первое закрытие после начала блока
insert_pos = found_closes[0] + len(model_info_end)

print(f"✅ Место для вставки найдено на позиции {insert_pos}")

# 3. Вставляем блок параметров после информации о модели
content = content[:insert_pos] + '\n\n      <!-- Параметры генерации (скрыты до выбора модели) -->\n      ' + params_block + content[insert_pos:]

# Сохраняем
with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Блок параметров успешно перемещён!")
print("\nТеперь структура:")
print("1. ✅ Промпт")
print("2. ✅ Выбор модели")
print("3. ✅ Информация о модели")
print("4. ✅ Параметры генерации (скрыты)")
print("5. ✅ Кнопка генерации")
print("6. ✅ Очередь генерации")
