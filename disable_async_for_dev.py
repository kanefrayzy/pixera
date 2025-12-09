"""
Скрипт для отключения асинхронной обработки в режиме разработки
Устанавливает USE_CELERY=False в .env файле
"""

import os
from pathlib import Path

def disable_async():
    """Отключает асинхронную обработку для разработки"""

    env_file = Path('.env')
    env_example = Path('.env.example')

    # Если .env не существует, создаём из .env.example
    if not env_file.exists():
        if env_example.exists():
            print("📋 Создаём .env из .env.example...")
            content = env_example.read_text(encoding='utf-8')
        else:
            print("❌ Файл .env.example не найден!")
            return False
    else:
        print("📋 Читаем существующий .env...")
        content = env_file.read_text(encoding='utf-8')

    # Заменяем USE_CELERY=True на USE_CELERY=False
    lines = content.split('\n')
    modified = False

    for i, line in enumerate(lines):
        if line.strip().startswith('USE_CELERY='):
            old_value = line.strip()
            lines[i] = 'USE_CELERY=False'
            if old_value != 'USE_CELERY=False':
                print(f"✏️  Изменено: {old_value} → USE_CELERY=False")
                modified = True
            else:
                print(f"✅ Уже установлено: USE_CELERY=False")
            break
    else:
        # Если USE_CELERY не найден, добавляем
        print("➕ Добавляем USE_CELERY=False")
        lines.append('USE_CELERY=False')
        modified = True

    # Сохраняем изменения
    if modified or not env_file.exists():
        env_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f"💾 Файл .env сохранён")

    print("\n" + "="*60)
    print("✅ АСИНХРОННАЯ ОБРАБОТКА ОТКЛЮЧЕНА")
    print("="*60)
    print("\n📝 Текущие настройки:")
    print("   • USE_CELERY=False (синхронная обработка)")
    print("   • Celery worker НЕ требуется")
    print("   • Redis НЕ требуется")
    print("   • Все задачи выполняются синхронно")
    print("\n🚀 Перезапустите сервер Django:")
    print("   python manage.py runserver")
    print("\n" + "="*60)

    return True

if __name__ == '__main__':
    disable_async()
