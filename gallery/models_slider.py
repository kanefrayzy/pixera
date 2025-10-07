import json
import os
from django.db import models, transaction
from django.db.models import Max
from django.conf import settings
from django.core.files.storage import default_storage


class SliderExample(models.Model):
    """Модель для управления примерами слайдера из JSON файла"""

    json_id = models.IntegerField(help_text="ID в JSON файле", blank=True, null=True, db_index=True)
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
    alt = models.CharField(max_length=200, verbose_name="Alt текст для изображения")

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

    order = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
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
            examples = cls.objects.filter(is_active=True).order_by('order', 'json_id')
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

        super().save(*args, **kwargs)

        # Автоматически экспортируем в JSON после сохранения
        if not kwargs.get('skip_export', False):
            self.export_to_json()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        # Автоматически экспортируем в JSON после удаления
        if not kwargs.get('skip_export', False):
            SliderExample.export_to_json()
