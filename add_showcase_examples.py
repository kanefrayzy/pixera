"""
Скрипт для добавления примеров showcase в базу данных
Запуск: python manage.py shell < add_showcase_examples.py
"""

from generate.models import ShowcaseCategory, ShowcaseImage
from django.contrib.auth import get_user_model

User = get_user_model()

# Получаем первого суперпользователя или создаем
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(is_staff=True).first()

# Создаем категории
categories_data = [
    {'name': 'Портреты', 'slug': 'portrait', 'order': 1},
    {'name': 'Мода', 'slug': 'fashion', 'order': 2},
    {'name': 'Арт', 'slug': 'art', 'order': 3},
    {'name': 'Природа', 'slug': 'nature', 'order': 4},
    {'name': 'Фэнтези', 'slug': 'fantasy', 'order': 5},
]

categories = {}
for cat_data in categories_data:
    cat, created = ShowcaseCategory.objects.get_or_create(
        slug=cat_data['slug'],
        defaults={
            'name': cat_data['name'],
            'order': cat_data['order'],
            'is_active': True
        }
    )
    categories[cat_data['slug']] = cat
    if created:
        print(f"✓ Создана категория: {cat.name}")
    else:
        print(f"→ Категория уже существует: {cat.name}")

# Примеры showcase (20 штук)
showcase_examples = [
    {
        'title': 'Элегантный портрет',
        'category': 'portrait',
        'prompt': 'Cinematic portrait of elegant woman, soft studio lighting, 85mm lens, shallow depth of field, warm color grading, professional photography, high detail',
        'image_url': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=80',
        'order': 1
    },
    {
        'title': 'Модный образ',
        'category': 'fashion',
        'prompt': 'High fashion editorial, dramatic lighting, luxury brand aesthetic, professional model, designer clothing, studio photography, vogue style, 50mm f/1.4',
        'image_url': 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&q=80',
        'order': 2
    },
    {
        'title': 'Цифровое искусство',
        'category': 'art',
        'prompt': 'Digital art masterpiece, vibrant colors, surreal composition, artistic interpretation, creative lighting, fantasy elements, 4K resolution, trending on artstation',
        'image_url': 'https://images.unsplash.com/photo-1549887534-1541e9326642?w=800&q=80',
        'order': 3
    },
    {
        'title': 'Горный пейзаж',
        'category': 'nature',
        'prompt': 'Majestic mountain landscape, golden hour lighting, dramatic clouds, wide angle lens, nature photography, HDR, breathtaking vista, professional landscape shot',
        'image_url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80',
        'order': 4
    },
    {
        'title': 'Фэнтези мир',
        'category': 'fantasy',
        'prompt': 'Epic fantasy scene, magical atmosphere, ethereal lighting, mystical creatures, enchanted forest, cinematic composition, concept art style, highly detailed',
        'image_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
        'order': 5
    },
    {
        'title': 'Студийный портрет',
        'category': 'portrait',
        'prompt': 'Professional studio portrait, Rembrandt lighting, black background, dramatic shadows, 105mm lens, f/2.8, high contrast, editorial style photography',
        'image_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&q=80',
        'order': 6
    },
    {
        'title': 'Уличная мода',
        'category': 'fashion',
        'prompt': 'Street fashion photography, urban background, natural lighting, candid moment, trendy outfit, lifestyle aesthetic, 35mm lens, shallow DOF, modern style',
        'image_url': 'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&q=80',
        'order': 7
    },
    {
        'title': 'Абстрактная композиция',
        'category': 'art',
        'prompt': 'Abstract art composition, bold colors, geometric shapes, modern design, minimalist aesthetic, creative concept, digital illustration, contemporary art style',
        'image_url': 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=800&q=80',
        'order': 8
    },
    {
        'title': 'Океанский закат',
        'category': 'nature',
        'prompt': 'Ocean sunset photography, golden hour, dramatic sky, long exposure, seascape, vibrant colors, peaceful atmosphere, professional nature shot, 24mm wide angle',
        'image_url': 'https://images.unsplash.com/photo-1505142468610-359e7d316be0?w=800&q=80',
        'order': 9
    },
    {
        'title': 'Космическая одиссея',
        'category': 'fantasy',
        'prompt': 'Space fantasy scene, nebula background, cosmic colors, sci-fi elements, futuristic aesthetic, cinematic lighting, epic scale, digital art masterpiece',
        'image_url': 'https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=800&q=80',
        'order': 10
    },
    {
        'title': 'Естественный свет',
        'category': 'portrait',
        'prompt': 'Natural light portrait, window lighting, soft shadows, authentic emotion, candid photography, 50mm f/1.8, warm tones, intimate atmosphere, lifestyle shot',
        'image_url': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&q=80',
        'order': 11
    },
    {
        'title': 'Высокая мода',
        'category': 'fashion',
        'prompt': 'Haute couture fashion, luxury brand campaign, professional styling, dramatic pose, editorial lighting, designer collection, runway aesthetic, 70mm medium format',
        'image_url': 'https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&q=80',
        'order': 12
    },
    {
        'title': 'Сюрреализм',
        'category': 'art',
        'prompt': 'Surrealist artwork, dreamlike atmosphere, impossible geometry, creative concept, artistic vision, vibrant palette, imaginative composition, digital painting',
        'image_url': 'https://images.unsplash.com/photo-1536924940846-227afb31e2a5?w=800&q=80',
        'order': 13
    },
    {
        'title': 'Лесная тропа',
        'category': 'nature',
        'prompt': 'Forest path photography, morning mist, soft natural light, green foliage, peaceful atmosphere, nature walk, wide angle landscape, serene environment',
        'image_url': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
        'order': 14
    },
    {
        'title': 'Драконий замок',
        'category': 'fantasy',
        'prompt': 'Fantasy castle scene, dragon flying, medieval architecture, epic scale, dramatic sky, magical atmosphere, concept art quality, highly detailed illustration',
        'image_url': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&q=80',
        'order': 15
    },
    {
        'title': 'Креативный портрет',
        'category': 'portrait',
        'prompt': 'Creative portrait photography, colored gels, experimental lighting, artistic expression, unique composition, bold colors, modern aesthetic, 85mm f/1.4',
        'image_url': 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&q=80',
        'order': 16
    },
    {
        'title': 'Минимализм в моде',
        'category': 'fashion',
        'prompt': 'Minimalist fashion photography, clean background, simple composition, elegant styling, neutral colors, modern aesthetic, professional lighting, editorial quality',
        'image_url': 'https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=800&q=80',
        'order': 17
    },
    {
        'title': 'Неоновые огни',
        'category': 'art',
        'prompt': 'Neon lights artwork, cyberpunk aesthetic, vibrant colors, urban night scene, futuristic vibe, digital art, glowing effects, contemporary style, 4K quality',
        'image_url': 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=800&q=80',
        'order': 18
    },
    {
        'title': 'Водопад в джунглях',
        'category': 'nature',
        'prompt': 'Jungle waterfall photography, lush vegetation, tropical paradise, long exposure water, natural beauty, adventure photography, wide angle shot, vibrant greens',
        'image_url': 'https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80',
        'order': 19
    },
    {
        'title': 'Магический портал',
        'category': 'fantasy',
        'prompt': 'Magical portal scene, mystical energy, glowing effects, fantasy landscape, otherworldly atmosphere, epic composition, concept art style, cinematic lighting',
        'image_url': 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80',
        'order': 20
    }
]

print("\n" + "="*60)
print("Добавление примеров showcase в базу данных")
print("="*60 + "\n")

# Добавляем примеры
from django.core.files.base import ContentFile
import requests

for idx, example in enumerate(showcase_examples, 1):
    try:
        # Проверяем, существует ли уже пример с таким заголовком
        existing = ShowcaseImage.objects.filter(title=example['title']).first()
        if existing:
            print(f"[{idx}/20] ⊘ Пример '{example['title']}' уже существует")
            continue
        
        # Скачиваем изображение
        print(f"[{idx}/20] ↓ Загрузка изображения для '{example['title']}'...")
        response = requests.get(example['image_url'], timeout=10)
        
        if response.status_code == 200:
            # Создаем запись
            img = ShowcaseImage(
                title=example['title'],
                category=categories.get(example['category']),
                prompt=example['prompt'],
                order=example['order'],
                is_active=True,
                uploaded_by=admin_user
            )
            
            # Сохраняем изображение
            filename = f"{example['category']}_{idx}.jpg"
            img.image.save(filename, ContentFile(response.content), save=True)
            
            print(f"[{idx}/20] ✓ Добавлен пример: {example['title']}")
        else:
            print(f"[{idx}/20] ✗ Ошибка загрузки изображения: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"[{idx}/20] ✗ Ошибка: {str(e)}")

print("\n" + "="*60)
print("Готово! Примеры добавлены в базу данных")
print("="*60)
print(f"\nВсего примеров в базе: {ShowcaseImage.objects.count()}")
print(f"Активных примеров: {ShowcaseImage.objects.filter(is_active=True).count()}")
print("\nТеперь обновите страницу генерации для просмотра результатов!")
