"""
Скрипт для подготовки данных категорий из изображений в static/img/category
"""
import os
from pathlib import Path

# Путь к директории с изображениями категорий
CATEGORY_DIR = Path("static/img/category")

def get_category_names():
    """Получить список названий категорий из файлов изображений"""
    if not CATEGORY_DIR.exists():
        print(f"Директория {CATEGORY_DIR} не найдена!")
        return []
    
    category_names = []
    
    # Получаем все .jpg файлы
    for file in sorted(CATEGORY_DIR.glob("*.jpg")):
        # Убираем расширение .jpg
        category_name = file.stem
        category_names.append(category_name)
    
    return category_names

def print_categories():
    """Вывести список категорий"""
    categories = get_category_names()
    
    print(f"\nНайдено категорий: {len(categories)}\n")
    print("Список категорий:")
    print("-" * 50)
    
    for i, cat in enumerate(categories, 1):
        print(f"{i:2d}. {cat}")
    
    print("-" * 50)
    print(f"\nВсего: {len(categories)} категорий")
    
    return categories

def generate_view_code():
    """Генерировать код для views.py"""
    categories = get_category_names()
    
    print("\n" + "=" * 70)
    print("КОД ДЛЯ ДОБАВЛЕНИЯ В generate/views.py:")
    print("=" * 70)
    
    code = f"""
# Список категорий для блока подсказок
CATEGORY_NAMES = {categories}

# В функции представления добавьте в context:
context['category_names'] = CATEGORY_NAMES
"""
    
    print(code)
    print("=" * 70)

if __name__ == "__main__":
    print("=" * 70)
    print("ПОДГОТОВКА ДАННЫХ КАТЕГОРИЙ")
    print("=" * 70)
    
    categories = print_categories()
    generate_view_code()
    
    print("\n✅ Готово! Скопируйте код выше в ваш views.py")
