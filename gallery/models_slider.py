import json
import os
from django.db import models, transaction
from django.db.models import Max
from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image


class SliderExample(models.Model):
    """Модель для управления примерами слайдера из JSON файла"""

    json_id = models.IntegerField(
        help_text="ID в JSON файле", blank=True, null=True, db_index=True)
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    prompt = models.TextField(verbose_name="Промт")
    image = models.ImageField(
        upload_to='slider_examples/',
        verbose_name="Изображение",
        help_text="Загрузите изображение для примера",
        blank=True,
        null=True
    )
    description = models.CharField(max_length=500, verbose_name="Описание")
    alt = models.CharField(
        max_length=200, verbose_name="Alt текст для изображения")

    # Настройки генерации
    steps = models.IntegerField(default=28, verbose_name="Количество шагов")
    cfg = models.FloatField(default=7.0, verbose_name="CFG Scale")
    # ratio убран - всегда используется 3:2
    seed = models.CharField(
        max_length=20,
        default="auto",
        verbose_name="Seed",
        help_text="Введите число или 'auto' для случайного"
    )

    order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Пример слайдера"
        verbose_name_plural = "Примеры слайдера"
        ordering = ['order', 'json_id']

    def __str__(self):
        return f"{self.title} (ID: {self.json_id})"

    @property
    def ratio(self):
        """Соотношение сторон всегда 3:2"""
        return "3:2"

    def save(self, *args, **kwargs):
        """Переопределяем save для базовых операций"""
        super().save(*args, **kwargs)

    @classmethod
    def get_json_file_path(cls):
        """Путь к JSON файлу"""
        return os.path.join(settings.BASE_DIR, 'static', 'data', 'slider_examples.json')

    @classmethod
    def load_from_json(cls):
        """Загрузить данные из JSON файла в базу данных"""
        json_path = cls.get_json_file_path()

        if not os.path.exists(json_path):
            return False, "JSON файл не найден"

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                obj, created = cls.objects.update_or_create(
                    json_id=item['id'],
                    defaults={
                        'title': item['title'],
                        'prompt': item['prompt'],
                        'description': item['description'],
                        'alt': item['alt'],
                        'steps': item['settings']['steps'],
                        'cfg': item['settings']['cfg'],
                        # ratio убран - всегда 3:2
                        'seed': str(item['settings']['seed']),
                        'order': item['id'],
                    }
                )

                # Для существующих записей, если изображение не задано,
                # попытаемся найти файл по пути из JSON
                if created or not obj.image:
                    image_path = item['image'].lstrip('/')
                    if os.path.exists(os.path.join(settings.BASE_DIR, image_path)):
                        # Здесь можно добавить логику копирования файла в media
                        pass

            return True, f"Загружено {len(data)} записей"

        except Exception as e:
            return False, f"Ошибка при загрузке: {str(e)}"

    @classmethod
    def export_to_json(cls):
        """Экспортировать активные записи в JSON файл"""
        json_path = cls.get_json_file_path()

        try:
            examples = cls.objects.filter(
                is_active=True).order_by('order', 'json_id')
            data = []

            for example in examples:
                # Формируем путь к изображению
                if example.image:
                    image_url = example.image.url
                else:
                    image_url = "/static/img/default.png"

                data.append({
                    "id": example.json_id,
                    "title": example.title,
                    "prompt": example.prompt,
                    "image": image_url,
                    "description": example.description,
                    "alt": example.alt,
                    "settings": {
                        "steps": example.steps,
                        "cfg": example.cfg,
                        "ratio": example.ratio,
                        "seed": example.seed if example.seed != "auto" else "auto"
                    }
                })

            # Создаем резервную копию
            if os.path.exists(json_path):
                backup_path = json_path + '.bak'
                import shutil
                shutil.copy2(json_path, backup_path)

            # Записываем новые данные
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True, f"Экспортировано {len(data)} записей"

        except Exception as e:
            return False, f"Ошибка при экспорте: {str(e)}"

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем json_id для новых записей
        if not self.json_id:
            max_id = SliderExample.objects.aggregate(
                models.Max('json_id')
            )['json_id__max']
            self.json_id = (max_id or -1) + 1

        # Сначала сохраняем как есть, чтобы получить путь к файлу
        super().save(*args, **kwargs)

        # Максимально сжать изображение (WebP, ширина до 960px)
        try:
            if self.image and getattr(self.image, "name", ""):
                try:
                    in_path = default_storage.path(self.image.name)
                except Exception:
                    in_path = None

                if in_path and os.path.exists(in_path):
                    # Подготовим выходной путь
                    base, _ = os.path.splitext(in_path)
                    out_path = base + "_cmp.webp"

                    # Открываем и конвертим
                    with Image.open(in_path) as im:
                        # Конвертируем в RGB (без альфы) для совместимости
                        if im.mode not in ("RGB", "L"):
                            im = im.convert("RGB")

                        # Ресайз по ширине до 960px (без увеличения)
                        w, h = im.size
                        max_w = 960
                        if w > max_w:
                            new_h = int(h * (max_w / float(w)))
                            im = im.resize((max_w, new_h), Image.LANCZOS)

                        # Сохранение в WebP с сильным сжатием
                        im.save(out_path, "WEBP", quality=70, method=6, optimize=True)

                    # Заменяем файл в поле image на сжатый
                    media_root = getattr(settings, "MEDIA_ROOT", "")
                    rel = os.path.relpath(out_path, media_root) if media_root and os.path.isabs(out_path) else out_path
                    rel = rel.replace("\\", "/")

                    if rel and rel != self.image.name:
                        self.image.name = rel
                        super(SliderExample, self).save(update_fields=["image"])
                        try:
                            # Удаляем исходник (без падения, если не удастся)
                            if os.path.exists(in_path):
                                os.remove(in_path)
                        except Exception:
                            pass
        except Exception:
            # Тихо игнорируем проблемы с Pillow/файловой системой
            pass

        # Экспортируем JSON после сохранения и возможной компрессии
        if not kwargs.get('skip_export', False):
            SliderExample.export_to_json()
