import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import PromptCategory

print("\n" + "="*70)
print("ПРОВЕРКА КАТЕГОРИЙ")
print("="*70 + "\n")

categories = PromptCategory.objects.all().order_by('order')[:10]

for cat in categories:
    has_image = bool(cat.image and cat.image.name)
    image_info = f"✅ {cat.image.url}" if has_image else "❌ Нет изображения"
    print(f"{cat.id:3d}. {cat.name:20s} - {image_info}")

print("\n" + "="*70)
print(f"Всего категорий: {PromptCategory.objects.count()}")
print(f"С изображениями: {PromptCategory.objects.exclude(image='').count()}")
print("="*70 + "\n")
