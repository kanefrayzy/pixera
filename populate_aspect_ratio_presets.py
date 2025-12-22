"""
Скрипт для заполнения предустановок соотношений сторон
Запуск: python manage.py shell < populate_aspect_ratio_presets.py
или: docker-compose exec web python manage.py shell < populate_aspect_ratio_presets.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models_aspect_ratio import AspectRatioPreset

# Данные для популярных соотношений
PRESETS = [
    # Квадратные
    {
        'aspect_ratio': '1:1',
        'name': 'Квадрат',
        'category': 'Соцсети',
        'icon': '🔲',
        'description': 'Instagram посты, иконки, аватары',
        'recommended_sd': '512x512',
        'recommended_hd': '720x720',
        'recommended_full_hd': '1080x1080',
        'recommended_2k': '1440x1440',
        'recommended_4k': '2160x2160',
        'recommended_8k': '4320x4320',
        'is_common': True,
        'order': 1
    },
    
    # Вертикальные (соцсети)
    {
        'aspect_ratio': '9:16',
        'name': 'Вертикальный Stories/Reels',
        'category': 'Соцсети',
        'icon': '📱',
        'description': 'Instagram Stories, TikTok, YouTube Shorts',
        'recommended_sd': '480x854',
        'recommended_hd': '720x1280',
        'recommended_full_hd': '1080x1920',
        'recommended_2k': '1440x2560',
        'recommended_4k': '2160x3840',
        'recommended_8k': '4320x7680',
        'is_common': True,
        'order': 2
    },
    {
        'aspect_ratio': '4:5',
        'name': 'Instagram портрет',
        'category': 'Соцсети',
        'icon': '📸',
        'description': 'Instagram вертикальные посты',
        'recommended_sd': '512x640',
        'recommended_hd': '720x900',
        'recommended_full_hd': '1080x1350',
        'recommended_2k': '1440x1800',
        'recommended_4k': '2160x2700',
        'is_common': True,
        'order': 3
    },
    {
        'aspect_ratio': '2:3',
        'name': 'Фотография 2:3',
        'category': 'Фотография',
        'icon': '📷',
        'description': 'Классическая фотопропорция',
        'recommended_sd': '480x720',
        'recommended_hd': '720x1080',
        'recommended_full_hd': '1080x1620',
        'recommended_2k': '1440x2160',
        'recommended_4k': '2160x3240',
        'is_common': False,
        'order': 4
    },
    {
        'aspect_ratio': '3:4',
        'name': 'Вертикальный стандарт',
        'category': 'Фотография',
        'icon': '🖼️',
        'description': 'Портретная фотография',
        'recommended_sd': '512x683',
        'recommended_hd': '720x960',
        'recommended_full_hd': '1080x1440',
        'recommended_2k': '1440x1920',
        'recommended_4k': '2160x2880',
        'is_common': False,
        'order': 5
    },
    
    # Горизонтальные широкоэкранные
    {
        'aspect_ratio': '16:9',
        'name': 'Широкоэкранный HD',
        'category': 'Видео/Мониторы',
        'icon': '🖥️',
        'description': 'YouTube, мониторы, телевизоры',
        'recommended_sd': '854x480',
        'recommended_hd': '1280x720',
        'recommended_full_hd': '1920x1080',
        'recommended_2k': '2560x1440',
        'recommended_4k': '3840x2160',
        'recommended_8k': '7680x4320',
        'is_common': True,
        'order': 10
    },
    {
        'aspect_ratio': '16:10',
        'name': 'Рабочий монитор',
        'category': 'Видео/Мониторы',
        'icon': '💻',
        'description': 'Ноутбуки, рабочие мониторы',
        'recommended_sd': '768x480',
        'recommended_hd': '1280x800',
        'recommended_full_hd': '1920x1200',
        'recommended_2k': '2560x1600',
        'recommended_4k': '3840x2400',
        'is_common': False,
        'order': 11
    },
    {
        'aspect_ratio': '21:9',
        'name': 'Ультраширокий',
        'category': 'Видео/Мониторы',
        'icon': '🎮',
        'description': 'Ультраширокие мониторы, киноэффект',
        'recommended_sd': '1024x439',
        'recommended_hd': '1280x549',
        'recommended_full_hd': '2560x1080',
        'recommended_2k': '3440x1440',
        'recommended_4k': '5120x2160',
        'is_common': False,
        'order': 12
    },
    
    # Классические
    {
        'aspect_ratio': '4:3',
        'name': 'Классический 4:3',
        'category': 'Классика',
        'icon': '📺',
        'description': 'Старые мониторы, CRT телевизоры',
        'recommended_sd': '640x480',
        'recommended_hd': '1024x768',
        'recommended_full_hd': '1440x1080',
        'recommended_2k': '1920x1440',
        'recommended_4k': '2880x2160',
        'is_common': False,
        'order': 20
    },
    {
        'aspect_ratio': '3:2',
        'name': 'Фотоаппараты',
        'category': 'Фотография',
        'icon': '📷',
        'description': '35mm плёнка, зеркальные камеры',
        'recommended_sd': '720x480',
        'recommended_hd': '1080x720',
        'recommended_full_hd': '1620x1080',
        'recommended_2k': '2160x1440',
        'recommended_4k': '3240x2160',
        'is_common': False,
        'order': 21
    },
    {
        'aspect_ratio': '5:4',
        'name': 'Старые LCD',
        'category': 'Классика',
        'icon': '🖵',
        'description': '1280×1024 мониторы',
        'recommended_sd': '640x512',
        'recommended_hd': '1280x1024',
        'recommended_full_hd': '1600x1280',
        'is_common': False,
        'order': 22
    },
    
    # Киноформаты
    {
        'aspect_ratio': '2.35:1',
        'name': 'CinemaScope',
        'category': 'Кино',
        'icon': '🎬',
        'description': 'Широкоэкранное кино',
        'recommended_sd': '1024x436',
        'recommended_hd': '1280x545',
        'recommended_full_hd': '2048x871',
        'recommended_2k': '2560x1089',
        'recommended_4k': '4096x1743',
        'is_common': False,
        'order': 30
    },
    {
        'aspect_ratio': '1.85:1',
        'name': 'Кинотеатры (Flat)',
        'category': 'Кино',
        'icon': '🎦',
        'description': 'Стандарт кинотеатров',
        'recommended_sd': '888x480',
        'recommended_hd': '1332x720',
        'recommended_full_hd': '1998x1080',
        'recommended_2k': '2664x1440',
        'recommended_4k': '3996x2160',
        'is_common': False,
        'order': 31
    },
    {
        'aspect_ratio': '2.39:1',
        'name': 'Современное кино',
        'category': 'Кино',
        'icon': '🎞️',
        'description': 'Anamorphic widescreen',
        'recommended_full_hd': '2048x857',
        'recommended_2k': '2560x1071',
        'recommended_4k': '4096x1714',
        'is_common': False,
        'order': 32
    },
    
    # Дополнительные соцсети
    {
        'aspect_ratio': '5:7',
        'name': 'Pinterest портрет',
        'category': 'Соцсети',
        'icon': '📌',
        'description': 'Pinterest оптимальный размер',
        'recommended_sd': '600x840',
        'recommended_hd': '720x1008',
        'recommended_full_hd': '1080x1512',
        'is_common': False,
        'order': 40
    },
    {
        'aspect_ratio': '10:16',
        'name': 'Вертикальный 10:16',
        'category': 'Соцсети',
        'icon': '📲',
        'description': 'Альтернативный вертикальный формат',
        'recommended_sd': '480x768',
        'recommended_hd': '720x1152',
        'recommended_full_hd': '1080x1728',
        'is_common': False,
        'order': 41
    },
]

def populate_presets():
    """Заполняет базу предустановками"""
    created_count = 0
    updated_count = 0
    
    for preset_data in PRESETS:
        preset, created = AspectRatioPreset.objects.update_or_create(
            aspect_ratio=preset_data['aspect_ratio'],
            defaults=preset_data
        )
        
        if created:
            created_count += 1
            print(f"✅ Создано: {preset}")
        else:
            updated_count += 1
            print(f"🔄 Обновлено: {preset}")
    
    print(f"\n📊 Итого:")
    print(f"   Создано: {created_count}")
    print(f"   Обновлено: {updated_count}")
    print(f"   Всего: {AspectRatioPreset.objects.count()}")

if __name__ == "__main__":
    print("🚀 Заполнение предустановок соотношений сторон...\n")
    populate_presets()
    print("\n✨ Готово!")
