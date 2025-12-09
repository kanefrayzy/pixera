"""
Скрипт для добавления дополнительных изображений к showcase примерам
Запуск: python manage.py shell < add_additional_showcase_images.py
"""

from generate.models import ShowcaseImage, ShowcaseAdditionalImage
from django.core.files.base import ContentFile
import requests

print("\n" + "="*60)
print("Добавление дополнительных изображений для слайдера")
print("="*60 + "\n")

# Дополнительные изображения для каждой категории
additional_images_data = {
    'portrait': [
        'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800&q=80',
        'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&q=80',
    ],
    'fashion': [
        'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=80',
        'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&q=80',
    ],
    'art': [
        'https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=800&q=80',
        'https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=800&q=80',
    ],
    'nature': [
        'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
        'https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=800&q=80',
    ],
    'fantasy': [
        'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80',
        'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
    ],
}

# Получаем все активные showcase примеры
showcase_items = ShowcaseImage.objects.filter(is_active=True).select_related('category')

total_added = 0

for item in showcase_items:
    category_slug = item.category.slug if item.category else 'misc'
    
    # Проверяем, есть ли уже дополнительные изображения
    existing_count = item.additional_images.count()
    if existing_count >= 2:
        print(f"⊘ '{item.title}' уже имеет {existing_count} доп. изображений")
        continue
    
    # Получаем URL изображений для этой категории
    image_urls = additional_images_data.get(category_slug, [])
    if not image_urls:
        print(f"⊘ Нет дополнительных изображений для категории '{category_slug}'")
        continue
    
    print(f"\n→ Добавление изображений для '{item.title}' ({category_slug})...")
    
    for idx, img_url in enumerate(image_urls[:2], 1):  # Максимум 2 дополнительных
        try:
            print(f"  [{idx}/2] Загрузка изображения...")
            response = requests.get(img_url, timeout=10)
            
            if response.status_code == 200:
                additional = ShowcaseAdditionalImage(
                    showcase=item,
                    order=idx,
                    is_active=True
                )
                
                filename = f"{category_slug}_additional_{item.id}_{idx}.jpg"
                additional.image.save(filename, ContentFile(response.content), save=True)
                
                print(f"  [{idx}/2] ✓ Добавлено дополнительное изображение #{idx}")
                total_added += 1
            else:
                print(f"  [{idx}/2] ✗ Ошибка загрузки: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [{idx}/2] ✗ Ошибка: {str(e)}")

print("\n" + "="*60)
print(f"Готово! Добавлено {total_added} дополнительных изображений")
print("="*60)

# Статистика
for item in ShowcaseImage.objects.filter(is_active=True):
    total_images = 1 + item.additional_images.filter(is_active=True).count()
    print(f"  • {item.title}: {total_images} изображений")

print("\nТеперь обновите страницу для просмотра слайдеров!")
