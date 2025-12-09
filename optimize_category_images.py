"""
Скрипт для оптимизации изображений категорий
Сжимает изображения до оптимального размера без потери качества
"""
import os
from PIL import Image
import sys

def optimize_image(input_path, output_path, max_size=(800, 800), quality=85):
    """
    Оптимизирует изображение
    
    Args:
        input_path: путь к исходному изображению
        output_path: путь для сохранения оптимизированного изображения
        max_size: максимальный размер (ширина, высота)
        quality: качество JPEG (1-100)
    """
    try:
        # Открываем изображение
        img = Image.open(input_path)
        
        # Конвертируем в RGB если необходимо
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Получаем текущий размер
        original_size = img.size
        
        # Вычисляем новый размер с сохранением пропорций
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Сохраняем оптимизированное изображение
        img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
        
        # Получаем размеры файлов
        original_file_size = os.path.getsize(input_path)
        optimized_file_size = os.path.getsize(output_path)
        reduction = ((original_file_size - optimized_file_size) / original_file_size) * 100
        
        print(f"✓ {os.path.basename(input_path)}")
        print(f"  Размер: {original_size[0]}x{original_size[1]} → {img.size[0]}x{img.size[1]}")
        print(f"  Файл: {original_file_size/1024:.1f}KB → {optimized_file_size/1024:.1f}KB ({reduction:.1f}% сжатие)")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка при обработке {input_path}: {e}")
        return False

def main():
    # Путь к папке с изображениями
    category_dir = 'static/img/category'
    
    if not os.path.exists(category_dir):
        print(f"Ошибка: Папка {category_dir} не найдена!")
        sys.exit(1)
    
    # Создаем резервную копию
    backup_dir = 'static/img/category_backup'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"Создана папка для резервных копий: {backup_dir}")
    
    print("\n" + "="*60)
    print("ОПТИМИЗАЦИЯ ИЗОБРАЖЕНИЙ КАТЕГОРИЙ")
    print("="*60 + "\n")
    
    # Получаем список всех изображений
    image_files = [f for f in os.listdir(category_dir) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    
    if not image_files:
        print("Изображения не найдены!")
        sys.exit(1)
    
    print(f"Найдено изображений: {len(image_files)}\n")
    
    success_count = 0
    total_original_size = 0
    total_optimized_size = 0
    
    for filename in sorted(image_files):
        input_path = os.path.join(category_dir, filename)
        backup_path = os.path.join(backup_dir, filename)
        
        # Создаем резервную копию если её ещё нет
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(input_path, backup_path)
        
        # Оптимизируем изображение
        # Для категорий используем размер 600x600 (квадрат) с качеством 85
        if optimize_image(input_path, input_path, max_size=(600, 600), quality=85):
            success_count += 1
        
        print()
    
    print("="*60)
    print(f"\nОбработано успешно: {success_count}/{len(image_files)}")
    print(f"Резервные копии сохранены в: {backup_dir}")
    print("\n" + "="*60)

if __name__ == '__main__':
    try:
        from PIL import Image
    except ImportError:
        print("Ошибка: Требуется установить Pillow")
        print("Выполните: pip install Pillow")
        sys.exit(1)
    
    main()
