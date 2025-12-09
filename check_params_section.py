#!/usr/bin/env python3
"""
Проверка наличия блока параметров в HTML
"""

print("🔍 Проверка блока параметров в new.html...\n")

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем блок параметров
if 'id="image-params-section"' in content:
    print("✅ Блок с id='image-params-section' найден")

    # Проверяем есть ли класс hidden
    if 'id="image-params-section" class="' in content or 'class="card p-6 mt-6 hidden" id="image-params-section"' in content or 'class="hidden' in content:
        # Находим строку с этим ID
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'id="image-params-section"' in line:
                print(f"\n📋 Строка {i+1}:")
                print(f"   {line.strip()}")

                # Проверяем класс hidden
                if 'hidden' in line:
                    print("   ✅ Класс 'hidden' присутствует")
                else:
                    print("   ❌ Класс 'hidden' отсутствует!")
                break

    # Проверяем расположение относительно image-model-info-section
    info_pos = content.find('id="image-model-info-section"')
    params_pos = content.find('id="image-params-section"')

    if info_pos > 0 and params_pos > 0:
        if params_pos > info_pos:
            print(f"\n✅ Блок параметров находится ПОСЛЕ блока информации о модели")
            print(f"   Позиция info: {info_pos}")
            print(f"   Позиция params: {params_pos}")
        else:
            print(f"\n❌ Блок параметров находится ДО блока информации о модели!")
            print(f"   Позиция info: {info_pos}")
            print(f"   Позиция params: {params_pos}")
else:
    print("❌ Блок с id='image-params-section' НЕ найден!")

print("\n✅ Проверка завершена!")
