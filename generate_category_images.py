"""
Скрипт для генерации изображений категорий промптов.
Создает простые, но красивые изображения для каждой категории.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from generate.models import PromptCategory
import io

# Цветовые схемы для разных категорий
CATEGORY_COLORS = {
    'Пейзажи': {
        'bg': [(34, 139, 34), (60, 179, 113), (46, 125, 50)],  # Зеленые тона
        'accent': (255, 255, 255),
        'emoji': '🏞️'
    },
    'Портреты': {
        'bg': [(255, 182, 193), (255, 160, 122), (255, 192, 203)],  # Розовые тона
        'accent': (255, 255, 255),
        'emoji': '👤'
    },
    'Фэнтези': {
        'bg': [(138, 43, 226), (147, 112, 219), (153, 50, 204)],  # Фиолетовые тона
        'accent': (255, 255, 255),
        'emoji': '🔮'
    },
    'Sci-Fi': {
        'bg': [(0, 191, 255), (30, 144, 255), (70, 130, 180)],  # Синие тона
        'accent': (255, 255, 255),
        'emoji': '🚀'
    },
    'Животные': {
        'bg': [(210, 180, 140), (222, 184, 135), (205, 133, 63)],  # Коричневые тона
        'accent': (255, 255, 255),
        'emoji': '🦁'
    },
    'Архитектура': {
        'bg': [(105, 105, 105), (128, 128, 128), (119, 136, 153)],  # Серые тона
        'accent': (255, 255, 255),
        'emoji': '🏛️'
    },
    'Абстракция': {
        'bg': [(255, 69, 0), (255, 140, 0), (255, 165, 0)],  # Оранжевые тона
        'accent': (255, 255, 255),
        'emoji': '🎨'
    },
    'Еда': {
        'bg': [(255, 99, 71), (255, 127, 80), (255, 160, 122)],  # Красно-оранжевые
        'accent': (255, 255, 255),
        'emoji': '🍕'
    },
    'Природа': {
        'bg': [(34, 139, 34), (50, 205, 50), (124, 252, 0)],  # Зеленые
        'accent': (255, 255, 255),
        'emoji': '🌿'
    },
    'Города': {
        'bg': [(70, 130, 180), (100, 149, 237), (135, 206, 250)],  # Голубые
        'accent': (255, 255, 255),
        'emoji': '🏙️'
    },
    'Космос': {
        'bg': [(25, 25, 112), (72, 61, 139), (106, 90, 205)],  # Темно-синие
        'accent': (255, 255, 255),
        'emoji': '🌌'
    },
    'Мода': {
        'bg': [(255, 20, 147), (255, 105, 180), (255, 182, 193)],  # Розовые
        'accent': (255, 255, 255),
        'emoji': '👗'
    },
    'Транспорт': {
        'bg': [(220, 20, 60), (178, 34, 34), (139, 0, 0)],  # Красные
        'accent': (255, 255, 255),
        'emoji': '🚗'
    },
    'Интерьер': {
        'bg': [(244, 164, 96), (210, 180, 140), (188, 143, 143)],  # Бежевые
        'accent': (255, 255, 255),
        'emoji': '🛋️'
    },
    'Искусство': {
        'bg': [(218, 165, 32), (184, 134, 11), (205, 133, 63)],  # Золотистые
        'accent': (255, 255, 255),
        'emoji': '🖼️'
    },
}

# Цвета по умолчанию для категорий без специфичной схемы
DEFAULT_COLORS = {
    'bg': [(99, 102, 241), (139, 92, 246), (168, 85, 247)],  # Фиолетово-синие
    'accent': (255, 255, 255),
    'emoji': '✨'
}


def create_gradient_background(width, height, colors):
    """Создает градиентный фон"""
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Создаем вертикальный градиент
    for y in range(height):
        # Интерполяция между цветами
        ratio = y / height
        if ratio < 0.5:
            # Первая половина: переход от первого ко второму цвету
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * (ratio * 2))
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * (ratio * 2))
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * (ratio * 2))
        else:
            # Вторая половина: переход от второго к третьему цвету
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * ((ratio - 0.5) * 2))
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * ((ratio - 0.5) * 2))
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * ((ratio - 0.5) * 2))
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return image


def create_category_image(category_name, width=800, height=600):
    """Создает изображение для категории"""
    # Получаем цветовую схему
    colors = CATEGORY_COLORS.get(category_name, DEFAULT_COLORS)
    
    # Создаем градиентный фон
    image = create_gradient_background(width, height, colors['bg'])
    draw = ImageDraw.Draw(image)
    
    # Добавляем полупрозрачный оверлей для лучшей читаемости текста
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 80))
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(image)
    
    # Пытаемся загрузить шрифт
    try:
        # Пробуем разные шрифты
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
        ]
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 80)
                emoji_font = ImageFont.truetype(font_path, 120)
                break
        
        if font is None:
            font = ImageFont.load_default()
            emoji_font = font
    except Exception:
        font = ImageFont.load_default()
        emoji_font = font
    
    # Рисуем эмодзи (если есть)
    emoji = colors.get('emoji', '✨')
    emoji_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
    emoji_width = emoji_bbox[2] - emoji_bbox[0]
    emoji_height = emoji_bbox[3] - emoji_bbox[1]
    emoji_x = (width - emoji_width) // 2
    emoji_y = height // 3 - emoji_height // 2
    
    # Тень для эмодзи
    draw.text((emoji_x + 3, emoji_y + 3), emoji, fill=(0, 0, 0, 128), font=emoji_font)
    draw.text((emoji_x, emoji_y), emoji, fill=colors['accent'], font=emoji_font)
    
    # Рисуем название категории
    text_bbox = draw.textbbox((0, 0), category_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) // 2
    text_y = height * 2 // 3 - text_height // 2
    
    # Тень для текста
    draw.text((text_x + 2, text_y + 2), category_name, fill=(0, 0, 0, 180), font=font)
    draw.text((text_x, text_y), category_name, fill=colors['accent'], font=font)
    
    return image


def update_categories_with_images():
    """Обновляет все категории, добавляя изображения"""
    categories = PromptCategory.objects.all()
    
    print(f"Найдено категорий: {categories.count()}")
    
    for category in categories:
        print(f"\nОбработка категории: {category.name}")
        
        # Создаем изображение
        image = create_category_image(category.name)
        
        # Сохраняем в BytesIO
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=90, optimize=True)
        buffer.seek(0)
        
        # Создаем имя файла
        filename = f"{category.slug}.jpg"
        
        # Сохраняем в модель
        category.image.save(filename, ContentFile(buffer.read()), save=True)
        
        print(f"✓ Изображение создано и сохранено: {filename}")
    
    print(f"\n✓ Все категории обновлены!")


if __name__ == '__main__':
    print("Начинаем генерацию изображений для категорий промптов...")
    update_categories_with_images()
    print("\nГотово!")
