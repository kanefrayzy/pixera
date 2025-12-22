"""
Image Model Configuration
Управление моделями генерации изображений с настройкой доступных параметров
"""
from django.db import models
from django.utils.text import slugify


class ImageModelConfiguration(models.Model):
    """
    Конфигурация модели генерации изображений.
    Администратор настраивает параметры один раз при создании модели.
    """

    # Основная информация
    name = models.CharField(
        "Название модели",
        max_length=100,
        help_text="Отображаемое название модели"
    )

    model_id = models.CharField(
        "ID модели Runware",
        max_length=100,
        unique=True,
        db_index=True,
        help_text="ID модели в формате provider:id@version (например: runware:101@1)"
    )

    slug = models.SlugField(
        "Слаг",
        max_length=120,
        unique=True,
        blank=True,
        db_index=True
    )

    description = models.TextField(
        "Описание",
        blank=True,
        default="",
        help_text="Описание модели для пользователей"
    )

    image = models.ImageField(
        "Изображение модели",
        upload_to="image_models/",
        blank=True,
        null=True,
        help_text="Превью модели"
    )

    # Провайдер и категория
    provider = models.CharField(
        "Провайдер",
        max_length=50,
        default="Runware",
        help_text="Название провайдера (Runware, ByteDance, BFL и т.д.)"
    )

    # Стоимость и лимиты
    token_cost = models.PositiveIntegerField(
        "Стоимость в токенах",
        default=10,
        help_text="Стоимость одной генерации"
    )

    # Разрешения (предустановленные)
    resolution_512x512 = models.BooleanField("512x512", default=False)
    resolution_512x768 = models.BooleanField("512x768", default=False)
    resolution_512x1024 = models.BooleanField("512x1024", default=False)
    resolution_768x512 = models.BooleanField("768x512", default=False)
    resolution_768x768 = models.BooleanField("768x768", default=False)
    resolution_768x1024 = models.BooleanField("768x1024", default=False)
    resolution_1024x512 = models.BooleanField("1024x512", default=False)
    resolution_1024x768 = models.BooleanField("1024x768", default=False)
    resolution_1024x1024 = models.BooleanField("1024x1024", default=True)
    resolution_1280x720 = models.BooleanField("1280x720 (HD)", default=False)
    resolution_1920x1080 = models.BooleanField("1920x1080 (Full HD)", default=False)
    resolution_2560x1440 = models.BooleanField("2560x1440 (2K)", default=False)
    resolution_3840x2160 = models.BooleanField("3840x2160 (4K)", default=False)

    # Поддержка произвольного разрешения
    supports_custom_resolution = models.BooleanField(
        "Поддерживает произвольное разрешение",
        default=False
    )

    min_width = models.PositiveIntegerField(
        "Минимальная ширина",
        default=512,
        null=True,
        blank=True,
        help_text="Минимальная ширина изображения в пикселях (устаревшее, используйте конфигурацию соотношений сторон)"
    )

    max_width = models.PositiveIntegerField(
        "Максимальная ширина",
        default=2048,
        null=True,
        blank=True,
        help_text="Максимальная ширина изображения в пикселях (устаревшее, используйте конфигурацию соотношений сторон)"
    )

    min_height = models.PositiveIntegerField(
        "Минимальная высота",
        default=512,
        null=True,
        blank=True,
        help_text="Минимальная высота изображения в пикселях (устаревшее, используйте конфигурацию соотношений сторон)"
    )

    max_height = models.PositiveIntegerField(
        "Максимальная высота",
        default=2048,
        null=True,
        blank=True,
        help_text="Максимальная высота изображения в пикселях (устаревшее, используйте конфигурацию соотношений сторон)"
    )

    # ============ ASPECT RATIO SETTINGS ============
    # 🔲 Квадратные
    aspect_ratio_1_1 = models.BooleanField("1:1 — квадрат (соцсети, иконки)", default=True)

    # 📺 Классические (старые мониторы / ТВ)
    aspect_ratio_4_3 = models.BooleanField("4:3 — стандарт (CRT, старые камеры)", default=False)
    aspect_ratio_3_2 = models.BooleanField("3:2 — фотоаппараты, плёнка", default=False)
    aspect_ratio_5_4 = models.BooleanField("5:4 — старые LCD (1280×1024)", default=False)

    # 🖥 Современные широкоэкранные
    aspect_ratio_16_9 = models.BooleanField("16:9 — основной стандарт (мониторы, ТВ, YouTube)", default=True)
    aspect_ratio_16_10 = models.BooleanField("16:10 — рабочие мониторы, ноутбуки", default=False)
    aspect_ratio_15_9 = models.BooleanField("15:9 — редкий переходный формат", default=False)
    aspect_ratio_17_9 = models.BooleanField("17:9 — цифровое кино (DCI)", default=False)

    # 🎬 Киноформаты
    aspect_ratio_1_85_1 = models.BooleanField("1.85:1 — кинотеатры (Flat)", default=False)
    aspect_ratio_2_00_1 = models.BooleanField("2.00:1 — Netflix, современные сериалы", default=False)
    aspect_ratio_2_20_1 = models.BooleanField("2.20:1 — 70mm плёнка", default=False)
    aspect_ratio_2_35_1 = models.BooleanField("2.35:1 — CinemaScope", default=False)
    aspect_ratio_2_39_1 = models.BooleanField("2.39:1 — CinemaScope", default=False)
    aspect_ratio_2_40_1 = models.BooleanField("2.40:1 — CinemaScope", default=False)

    # 🖥 Ультраширокие
    aspect_ratio_18_9 = models.BooleanField("18:9 (≈2:1)", default=False)
    aspect_ratio_19_9 = models.BooleanField("19:9", default=False)
    aspect_ratio_20_9 = models.BooleanField("20:9", default=False)
    aspect_ratio_21_9 = models.BooleanField("21:9 — ультраширокие мониторы", default=False)
    aspect_ratio_24_10 = models.BooleanField("24:10", default=False)
    aspect_ratio_32_9 = models.BooleanField("32:9 — суперультраширокие", default=False)

    # 📱 Вертикальные (мобильные, соцсети)
    aspect_ratio_9_16 = models.BooleanField("9:16 — основной вертикальный (Stories, Reels)", default=True)
    aspect_ratio_3_4 = models.BooleanField("3:4 — вертикальный стандарт", default=False)
    aspect_ratio_2_3 = models.BooleanField("2:3 — фото", default=False)
    aspect_ratio_4_5 = models.BooleanField("4:5 — Instagram", default=False)
    aspect_ratio_5_8 = models.BooleanField("5:8", default=False)
    aspect_ratio_10_16 = models.BooleanField("10:16", default=False)
    aspect_ratio_9_19_5 = models.BooleanField("9:19.5", default=False)
    aspect_ratio_9_20 = models.BooleanField("9:20", default=False)
    aspect_ratio_9_21 = models.BooleanField("9:21", default=False)

    # 🖼 Фотографические
    aspect_ratio_7_5 = models.BooleanField("7:5", default=False)
    aspect_ratio_8_10 = models.BooleanField("8:10 — портретная печать", default=False)

    # Параметры генерации
    supports_steps = models.BooleanField(
        "Поддерживает настройку шагов",
        default=True,
        help_text="Inference steps"
    )

    min_steps = models.PositiveIntegerField("Минимум шагов", default=1, blank=True)
    max_steps = models.PositiveIntegerField("Максимум шагов", default=50, blank=True)
    default_steps = models.PositiveIntegerField("Шагов по умолчанию", default=20, blank=True)

    supports_cfg_scale = models.BooleanField(
        "Поддерживает CFG Scale",
        default=True,
        help_text="Guidance scale"
    )

    min_cfg_scale = models.DecimalField(
        "Минимум CFG",
        max_digits=4,
        decimal_places=1,
        default=1.0,
        blank=True
    )

    max_cfg_scale = models.DecimalField(
        "Максимум CFG",
        max_digits=4,
        decimal_places=1,
        default=20.0,
        blank=True
    )

    default_cfg_scale = models.DecimalField(
        "CFG по умолчанию",
        max_digits=4,
        decimal_places=1,
        default=7.0,
        blank=True
    )

    supports_scheduler = models.BooleanField(
        "Поддерживает выбор scheduler",
        default=True
    )

    supports_seed = models.BooleanField(
        "Поддерживает seed",
        default=True
    )

    supports_negative_prompt = models.BooleanField(
        "Поддерживает негативный промпт",
        default=True
    )

    supports_reference_images = models.BooleanField(
        "Поддерживает референсные изображения",
        default=False,
        help_text="Модель поддерживает референсные изображения (FLUX.1 Kontext, Ace++)"
    )

    max_reference_images = models.PositiveIntegerField(
        "Максимум референсов",
        default=1,
        blank=True,
        help_text="Максимальное количество референсных изображений (1-2)"
    )

    # Специальные параметры для определённых моделей
    is_special_model = models.BooleanField(
        "Специальная модель",
        default=False,
        help_text="Модель требует особой обработки (Flux, Seedream и т.д.)"
    )

    uses_jpeg_format = models.BooleanField(
        "Использует JPEG формат",
        default=False,
        help_text="Для специальных моделей (Flux, Seedream)"
    )

    include_cost_in_request = models.BooleanField(
        "Включать стоимость в запрос",
        default=False,
        help_text="Добавлять includeCost в запрос (для специальных моделей)"
    )

    # Количество результатов
    supports_multiple_results = models.BooleanField(
        "Поддерживает несколько результатов",
        default=True
    )

    max_number_results = models.PositiveIntegerField(
        "Максимум результатов",
        default=4,
        blank=True,
        help_text="Максимальное количество изображений за раз"
    )

    # Метаданные
    is_active = models.BooleanField(
        "Активна",
        default=True,
        db_index=True
    )

    is_beta = models.BooleanField(
        "Бета-версия",
        default=False
    )

    is_premium = models.BooleanField(
        "Премиум модель",
        default=False
    )

    order = models.PositiveIntegerField(
        "Порядок",
        default=0,
        db_index=True,
        help_text="Порядок отображения в списке (меньше = выше)"
    )

    admin_notes = models.TextField(
        "Заметки администратора",
        blank=True,
        default="",
        help_text="Внутренние заметки (не видны пользователям)"
    )

    # Доступные параметры для пользователя (JSON)
    optional_fields = models.JSONField(
        "Доступные параметры",
        default=dict,
        blank=True,
        help_text="Какие поля показывать пользователю при генерации"
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('order', 'name')
        verbose_name = "Конфигурация модели изображений"
        verbose_name_plural = "Конфигурации моделей изображений"
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['provider', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.model_id})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or self.model_id)[:120]
        super().save(*args, **kwargs)

    def get_available_resolutions(self):
        """Возвращает список доступных разрешений"""
        resolutions = []
        resolution_fields = [
            ('resolution_512x512', '512x512'),
            ('resolution_512x768', '512x768'),
            ('resolution_512x1024', '512x1024'),
            ('resolution_768x512', '768x512'),
            ('resolution_768x768', '768x768'),
            ('resolution_768x1024', '768x1024'),
            ('resolution_1024x512', '1024x512'),
            ('resolution_1024x768', '1024x768'),
            ('resolution_1024x1024', '1024x1024'),
            ('resolution_1280x720', '1280x720'),
            ('resolution_1920x1080', '1920x1080'),
            ('resolution_2560x1440', '2560x1440'),
            ('resolution_3840x2160', '3840x2160'),
        ]

        for field_name, resolution in resolution_fields:
            if getattr(self, field_name, False):
                resolutions.append(resolution)

        return resolutions

    def get_available_aspect_ratios(self):
        """Возвращает список доступных соотношений сторон"""
        ratios = []
        ratio_fields = [
            # 🔲 Квадратные
            ('1:1', self.aspect_ratio_1_1),

            # 📺 Классические
            ('4:3', self.aspect_ratio_4_3),
            ('3:2', self.aspect_ratio_3_2),
            ('5:4', self.aspect_ratio_5_4),

            # 🖥 Современные широкоэкранные
            ('16:9', self.aspect_ratio_16_9),
            ('16:10', self.aspect_ratio_16_10),
            ('15:9', self.aspect_ratio_15_9),
            ('17:9', self.aspect_ratio_17_9),

            # 🎬 Киноформаты
            ('1.85:1', self.aspect_ratio_1_85_1),
            ('2.00:1', self.aspect_ratio_2_00_1),
            ('2.20:1', self.aspect_ratio_2_20_1),
            ('2.35:1', self.aspect_ratio_2_35_1),
            ('2.39:1', self.aspect_ratio_2_39_1),
            ('2.40:1', self.aspect_ratio_2_40_1),

            # 🖥 Ультраширокие
            ('18:9', self.aspect_ratio_18_9),
            ('19:9', self.aspect_ratio_19_9),
            ('20:9', self.aspect_ratio_20_9),
            ('21:9', self.aspect_ratio_21_9),
            ('24:10', self.aspect_ratio_24_10),
            ('32:9', self.aspect_ratio_32_9),

            # 📱 Вертикальные
            ('9:16', self.aspect_ratio_9_16),
            ('3:4', self.aspect_ratio_3_4),
            ('2:3', self.aspect_ratio_2_3),
            ('4:5', self.aspect_ratio_4_5),
            ('5:8', self.aspect_ratio_5_8),
            ('10:16', self.aspect_ratio_10_16),
            ('9:19.5', self.aspect_ratio_9_19_5),
            ('9:20', self.aspect_ratio_9_20),
            ('9:21', self.aspect_ratio_9_21),

            # 🖼 Фотографические
            ('7:5', self.aspect_ratio_7_5),
            ('8:10', self.aspect_ratio_8_10),
        ]
        for ratio, enabled in ratio_fields:
            if enabled:
                ratios.append(ratio)
        return ratios

    def is_special_processing_model(self):
        """Проверяет, требует ли модель специальной обработки"""
        model_lower = str(self.model_id).lower()
        return model_lower in {"bfl:2@2", "bytedance:5@0"} or self.is_special_model

    def get_default_resolution(self):
        """Возвращает разрешение по умолчанию"""
        available = self.get_available_resolutions()
        if available:
            return available[0]
        return "1024x1024"

    def to_json(self):
        """Serialize model data for JavaScript"""
        import json

        # Получаем optional_fields из JSON поля или создаем дефолтные
        optional_fields = self.optional_fields if self.optional_fields else {}

        # Если optional_fields пустой, заполняем на основе supports_* полей
        if not optional_fields:
            optional_fields = {
                'resolution': True,  # всегда показываем
                'steps': self.supports_steps,
                'cfg_scale': self.supports_cfg_scale,
                'scheduler': self.supports_scheduler,
                'seed': self.supports_seed,
                'negative_prompt': self.supports_negative_prompt,
                'reference_images': self.supports_reference_images,
                'number_results': self.supports_multiple_results,
                'prompt': True,  # всегда доступен
                'auto_translate': True,  # всегда доступен
                'prompt_generator': True,  # всегда доступен
            }

        return json.dumps({
            'id': self.id,
            'name': self.name,
            'model_id': self.model_id,
            'description': self.description or '',
            'token_cost': self.token_cost,
            'optional_fields': optional_fields,
            'available_resolutions': self.get_available_resolutions(),
            'available_aspect_ratios': self.get_available_aspect_ratios(),
            'min_width': self.min_width,
            'max_width': self.max_width,
            'min_height': self.min_height,
            'max_height': self.max_height,
            'min_steps': self.min_steps,
            'max_steps': self.max_steps,
            'default_steps': self.default_steps,
            'min_cfg_scale': float(self.min_cfg_scale) if self.min_cfg_scale else 1.0,
            'max_cfg_scale': float(self.max_cfg_scale) if self.max_cfg_scale else 20.0,
            'default_cfg_scale': float(self.default_cfg_scale) if self.default_cfg_scale else 7.0,
            'max_reference_images': self.max_reference_images,
            'max_number_results': self.max_number_results,
            'supports_steps': self.supports_steps,
            'supports_cfg_scale': self.supports_cfg_scale,
            'supports_scheduler': self.supports_scheduler,
            'supports_seed': self.supports_seed,
            'supports_negative_prompt': self.supports_negative_prompt,
            'supports_reference_images': self.supports_reference_images,
            'supports_multiple_results': self.supports_multiple_results,
        })
