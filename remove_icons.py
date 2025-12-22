import re

# Читаем файл
with open('populate_aspect_ratio_presets.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем все строки с 'icon'
content = re.sub(r"\s*'icon':\s*'[^']*',\n", '', content)

# Записываем обратно
with open('populate_aspect_ratio_presets.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Removed all icon fields from populate_aspect_ratio_presets.py')
