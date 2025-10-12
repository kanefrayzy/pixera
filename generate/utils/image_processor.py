"""
Утилиты для обработки изображений перед отправкой в API.
"""

import io
import logging
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)


def process_image_for_video(image_file, max_size=(1024, 1024), quality=85):
    """
    Обрабатывает и оптимизирует изображение для генерации видео.
    
    Args:
        image_file: Загруженный файл изображения
        max_size: Максимальный размер (ширина, высота)
        quality: Качество JPEG (1-100)
        
    Returns:
        InMemoryUploadedFile: Обработанное изображение
    """
    try:
        # Открываем изображение
        img = Image.open(image_file)
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон для прозрачных изображений
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Получаем оригинальные размеры
        original_width, original_height = img.size
        logger.info(f"Оригинальный размер изображения: {original_width}x{original_height}")
        
        # Вычисляем новые размеры с сохранением пропорций
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        new_width, new_height = img.size
        
        logger.info(f"Новый размер изображения: {new_width}x{new_height}")
        
        # Сохраняем в буфер
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Создаем новый файл
        processed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_file.name.split('.')[0]}_processed.jpg",
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
        
        logger.info(f"Изображение обработано: {output.getbuffer().nbytes / 1024:.2f} KB")
        
        return processed_file
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        # Возвращаем оригинал если не удалось обработать
        image_file.seek(0)
        return image_file


def get_optimal_video_dimensions(image_file):
    """
    Определяет оптимальные размеры видео на основе изображения.
    
    Args:
        image_file: Загруженный файл изображения
        
    Returns:
        tuple: (aspect_ratio, resolution)
    """
    try:
        img = Image.open(image_file)
        width, height = img.size
        image_file.seek(0)  # Возвращаем указатель в начало
        
        # Определяем соотношение сторон
        ratio = width / height
        
        if ratio > 1.5:  # Широкое изображение
            aspect_ratio = '16:9'
            resolution = '1280x720'
        elif ratio < 0.7:  # Вертикальное изображение
            aspect_ratio = '9:16'
            resolution = '720x1280'
        else:  # Квадратное или близкое к нему
            aspect_ratio = '1:1'
            resolution = '1024x1024'
        
        logger.info(f"Определены параметры видео: {aspect_ratio}, {resolution} (исходное соотношение: {ratio:.2f})")
        
        return aspect_ratio, resolution
        
    except Exception as e:
        logger.error(f"Ошибка при определении размеров: {e}")
        return '16:9', '1280x720'  # Значения по умолчанию
