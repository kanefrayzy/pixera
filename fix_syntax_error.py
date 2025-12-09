#!/usr/bin/env python3
"""
Исправление синтаксической ошибки в video-generation.js
"""

with open('static/js/video-generation.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Находим строку с ошибкой
for i, line in enumerate(lines):
    if 'updateModelInfo() {' in line and i > 0:
        # Проверяем предыдущую строку
        prev_line = lines[i-1].strip()
        if prev_line == '}':
            # Уже исправлено
            print("✓ Файл уже исправлен")
            break
        elif '/**' in lines[i-1]:
            # Нужно добавить } перед комментарием
            # Ищем строку с contentEl.innerHTML
            for j in range(i-1, max(0, i-20), -1):
                if 'contentEl.innerHTML = this.escapeHtml(description);' in lines[j]:
                    # Добавляем } после этой строки
                    lines.insert(j+1, '  }\n\n')
                    print(f"✓ Добавлена закрывающая скобка после строки {j+1}")
                    break
            break

# Сохраняем исправленный файл
with open('static/js/video-generation.js', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Файл сохранён")
