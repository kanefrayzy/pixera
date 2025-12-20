"""
Enhanced Video Model with all Runware API parameters
Supports comprehensive configuration for video generation
"""
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Допустимые значения FPS для видео‑моделей
VALID_FPS = (15, 24, 30, 60, 90, 120)


class VideoModelConfiguration(models.Model):
    """
    Comprehensive video model configuration with all Runware parameters.
    Allows admin to configure which parameters are available for each model.
    """

    # Basic Information
    name = models.CharField("Название модели", max_length=100)
    model_id = models.CharField("ID модели Runware", max_length=100, db_index=True)
    slug = models.SlugField("Слаг", max_length=120, unique=True, db_index=True)
    description = models.TextField("Описание", blank=True, default="")

    # Model Image/Preview
    image = models.ImageField(
        "Изображение модели",
        upload_to="video_models/%Y/%m/",
        blank=True,
        null=True,
        help_text="Превью или иконка модели для отображения в интерфейсе"
    )

    # Category - Only T2V and I2V
    class Category(models.TextChoices):
        T2V = "t2v", "Text-to-Video (Генерация видео)"
        I2V = "i2v", "Image-to-Video (Оживить фото)"

    category = models.CharField(
        "Категория",
        max_length=20,
        choices=Category.choices,
        default=Category.T2V,
        db_index=True,
        help_text="T2V = модель появится в 'Генерация видео', I2V = модель появится в 'Оживить фото'"
    )

    # Pricing
    token_cost = models.PositiveIntegerField("Стоимость в токенах", default=18)

    # ============ RESOLUTION SETTINGS ============
    # Available resolutions (checkbox selection)
    supports_custom_resolution = models.BooleanField("Поддерживает произвольное разрешение", default=False)

    # Predefined resolutions
    resolution_512x512 = models.BooleanField("512x512", default=False)
    resolution_512x768 = models.BooleanField("512x768", default=False)
    resolution_512x1024 = models.BooleanField("512x1024", default=False)
    resolution_768x512 = models.BooleanField("768x512", default=False)
    resolution_768x768 = models.BooleanField("768x768", default=False)
    resolution_768x1024 = models.BooleanField("768x1024", default=False)
    resolution_1024x512 = models.BooleanField("1024x512", default=False)
    resolution_1024x768 = models.BooleanField("1024x768", default=False)
    resolution_1024x1024 = models.BooleanField("1024x1024", default=True)
    resolution_1280x720 = models.BooleanField("1280x720 (HD)", default=True)
    resolution_1920x1080 = models.BooleanField("1920x1080 (Full HD)", default=True)
    resolution_2560x1440 = models.BooleanField("2560x1440 (2K)", default=False)
    resolution_3840x2160 = models.BooleanField("3840x2160 (4K)", default=False)

    # Custom resolution limits
    min_width = models.PositiveIntegerField("Минимальная ширина", default=512)
    max_width = models.PositiveIntegerField("Максимальная ширина", default=1920)
    min_height = models.PositiveIntegerField("Минимальная высота", default=512)
    max_height = models.PositiveIntegerField("Максимальная высота", default=1080)

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

    # ============ DURATION SETTINGS ============
    supports_custom_duration = models.BooleanField("Поддерживает произвольную длительность", default=False)

    # Predefined durations (in seconds)
    duration_2 = models.BooleanField("2 секунды", default=False)
    duration_3 = models.BooleanField("3 секунды", default=False)
    duration_4 = models.BooleanField("4 секунды", default=True)
    duration_5 = models.BooleanField("5 секунды", default=True)
    duration_6 = models.BooleanField("6 секунд", default=False)
    duration_8 = models.BooleanField("8 секунд", default=True)
    duration_10 = models.BooleanField("10 секунд", default=True)
    duration_12 = models.BooleanField("12 секунд", default=False)
    duration_15 = models.BooleanField("15 секунд", default=False)
    duration_20 = models.BooleanField("20 секунд", default=False)
    duration_30 = models.BooleanField("30 секунд", default=False)

    # Duration limits
    min_duration = models.PositiveIntegerField("Минимальная длительность (сек)", default=2)
    max_duration = models.PositiveIntegerField("Максимальная длительность (сек)", default=10)

    # ============ CAMERA MOVEMENT SETTINGS ============
    supports_camera_movement = models.BooleanField("Поддерживает движение камеры", default=True)

    camera_static = models.BooleanField("Статичная камера", default=True)
    camera_pan_left = models.BooleanField("Панорама влево", default=True)
    camera_pan_right = models.BooleanField("Панорама вправо", default=True)
    camera_tilt_up = models.BooleanField("Наклон вверх", default=True)
    camera_tilt_down = models.BooleanField("Наклон вниз", default=True)
    camera_zoom_in = models.BooleanField("Приближение", default=True)
    camera_zoom_out = models.BooleanField("Отдаление", default=True)
    camera_dolly_in = models.BooleanField("Движение вперёд", default=False)
    camera_dolly_out = models.BooleanField("Движение назад", default=False)
    camera_orbit_left = models.BooleanField("Орбита влево", default=False)
    camera_orbit_right = models.BooleanField("Орбита вправо", default=False)
    camera_crane_up = models.BooleanField("Кран вверх", default=False)
    camera_crane_down = models.BooleanField("Кран вниз", default=False)

    # ============ IMAGE-TO-VIDEO SETTINGS ============
    supports_image_to_video = models.BooleanField("Поддерживает Image-to-Video", default=False)

    # Motion strength for I2V
    supports_motion_strength = models.BooleanField("Поддерживает силу движения", default=False)
    min_motion_strength = models.PositiveIntegerField("Минимальная сила движения", default=0, blank=True, null=True)
    max_motion_strength = models.PositiveIntegerField("Максимальная сила движения", default=100, blank=True, null=True)
    default_motion_strength = models.PositiveIntegerField("Сила движения по умолчанию", default=45, blank=True, null=True)

    # ============ ADVANCED PARAMETERS ============
    # Seed support
    supports_seed = models.BooleanField("Поддерживает seed", default=True)

    # FPS settings
    supports_fps = models.BooleanField("Поддерживает настройку FPS", default=False)
    # Predefined FPS values (checkboxes)
    fps_15 = models.BooleanField("15 FPS", default=False)
    fps_24 = models.BooleanField("24 FPS", default=True)
    fps_30 = models.BooleanField("30 FPS", default=True)
    fps_60 = models.BooleanField("60 FPS", default=False)
    fps_90 = models.BooleanField("90 FPS", default=False)
    fps_120 = models.BooleanField("120 FPS", default=False)
    # Legacy fields (kept for backward compatibility)
    min_fps = models.PositiveIntegerField("Минимальный FPS", default=24, blank=True, null=True)
    max_fps = models.PositiveIntegerField("Максимальный FPS", default=60, blank=True, null=True)
    default_fps = models.PositiveIntegerField("FPS по умолчанию", default=30, blank=True, null=True)

    # Quality settings
    supports_quality = models.BooleanField("Поддерживает настройку качества", default=False)
    quality_low = models.BooleanField("Низкое качество", default=False)
    quality_medium = models.BooleanField("Среднее качество", default=True)
    quality_high = models.BooleanField("Высокое качество", default=True)
    quality_ultra = models.BooleanField("Ультра качество", default=False)

    # Style presets
    supports_style_presets = models.BooleanField("Поддерживает стилевые пресеты", default=False)
    style_realistic = models.BooleanField("Реалистичный", default=False)
    style_anime = models.BooleanField("Аниме", default=False)
    style_cartoon = models.BooleanField("Мультяшный", default=False)
    style_cinematic = models.BooleanField("Кинематографичный", default=False)
    style_artistic = models.BooleanField("Художественный", default=False)

    # Negative prompt support
    supports_negative_prompt = models.BooleanField("Поддерживает негативный промпт", default=True)

    # Reference images support
    supports_reference_images = models.BooleanField("Поддерживает референсные изображения", default=False)

    # ============ REFERENCE TYPES SETTINGS ============
    supported_references = models.JSONField(
        "Поддерживаемые референсы",
        default=list,
        blank=True,
        help_text="Типы входных данных: frameImages, referenceImages, audioInputs, controlNet"
    )

    # ============ MULTIPLE VIDEOS SETTINGS ============
    supports_multiple_videos = models.BooleanField("Поддерживает множественную генерацию", default=False, help_text="Позволяет генерировать несколько видео за раз")
    min_videos = models.PositiveIntegerField("Минимум видео", default=1, blank=True, null=True)
    max_videos = models.PositiveIntegerField("Максимум видео", default=4, blank=True, null=True)
    default_videos = models.PositiveIntegerField("Количество по умолчанию", default=1, blank=True, null=True)

    # Guidance scale
    supports_guidance_scale = models.BooleanField("Поддерживает guidance scale", default=False)
    min_guidance_scale = models.FloatField("Минимальный guidance scale", default=1.0, blank=True, null=True)
    max_guidance_scale = models.FloatField("Максимальный guidance scale", default=20.0, blank=True, null=True)
    default_guidance_scale = models.FloatField("Guidance scale по умолчанию", default=7.5, blank=True, null=True)

    # Number of inference steps
    supports_inference_steps = models.BooleanField("Поддерживает количество шагов", default=False)
    min_inference_steps = models.PositiveIntegerField("Минимум шагов", default=10, blank=True, null=True)
    max_inference_steps = models.PositiveIntegerField("Максимум шагов", default=100, blank=True, null=True)
    default_inference_steps = models.PositiveIntegerField("Шагов по умолчанию", default=50, blank=True, null=True)

    # ============ OUTPUT SETTINGS ============
    # Output format
    supports_mp4 = models.BooleanField("Поддерживает MP4", default=True)
    supports_webm = models.BooleanField("Поддерживает WebM", default=False)
    supports_gif = models.BooleanField("Поддерживает GIF", default=False)

    # Watermark
    supports_watermark_removal = models.BooleanField("Поддерживает удаление водяного знака", default=False)

    # ============ METADATA ============
    is_active = models.BooleanField("Активна", default=True, db_index=True)
    is_beta = models.BooleanField("Бета-версия", default=False)
    is_premium = models.BooleanField("Премиум модель", default=False)

    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)

    # Provider info
    provider = models.CharField("Провайдер", max_length=50, default="Runware")
    provider_version = models.CharField("Версия провайдера", max_length=50, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional notes
    admin_notes = models.TextField("Заметки администратора", blank=True, default="")

    # Optional fields configuration (JSON)
    optional_fields = models.JSONField(
        "Опциональные поля",
        default=dict,
        blank=True,
        help_text="JSON конфигурация доступных полей для пользователя"
    )

    class Meta:
        verbose_name = "Конфигурация видео модели"
        verbose_name_plural = "Конфигурации видео моделей"
        ordering = ("order", "name")
        unique_together = [['model_id', 'category']]
        indexes = [
            models.Index(fields=["is_active", "category", "order"]),
            models.Index(fields=["is_active", "is_premium", "order"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.model_id})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name or "")[:110]  # Leave room for suffix
            # Add category suffix to make slug unique
            self.slug = f"{base_slug}-{self.category}"

        # Compress image only if it's a new upload (has changed)
        if self.image and hasattr(self.image, 'file'):
            try:
                # Check if this is a new upload by seeing if the file has been read
                if not self.pk or (self.pk and self._state.adding):
                    # New instance - compress
                    self.image = self.compress_image(self.image)
                else:
                    # Existing instance - check if image changed
                    try:
                        old_instance = VideoModelConfiguration.objects.get(pk=self.pk)
                        if old_instance.image != self.image:
                            # Image changed - compress
                            self.image = self.compress_image(self.image)
                    except VideoModelConfiguration.DoesNotExist:
                        # New instance - compress
                        self.image = self.compress_image(self.image)
            except Exception as e:
                # If compression fails, just save the original
                print(f"Image compression skipped: {e}")

        super().save(*args, **kwargs)

    def compress_image(self, image_field):
        """
        Compress uploaded image to reduce file size while maintaining quality
        Max width: 1200px, Quality: 90% for better clarity on cards
        """
        try:
            # Open the image
            img = Image.open(image_field)

            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Resize if image is too large (увеличено до 1200px для лучшего качества)
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save to BytesIO (увеличено качество до 90%)
            output = BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            output.seek(0)

            # Preserve the original filename, just change extension to .jpg
            import os
            original_name = image_field.name
            name_without_ext = os.path.splitext(original_name)[0]
            new_name = f"{name_without_ext}.jpg"

            # Create new InMemoryUploadedFile
            return InMemoryUploadedFile(
                output,
                'ImageField',
                new_name,
                'image/jpeg',
                sys.getsizeof(output),
                None
            )
        except Exception as e:
            # If compression fails, return original image
            print(f"Image compression failed: {e}")
            return image_field

    # ============ COMPATIBILITY METHODS FOR JAVASCRIPT ============

    @property
    def runware_model_id(self):
        """Alias for model_id to match JavaScript expectations"""
        return self.model_id

    def get_category_for_js(self):
        """Returns category in format expected by JavaScript ('t2v', 'i2v', 'both')"""
        return self.category

    def is_available_for_t2v(self):
        """Check if model is available for Text-to-Video"""
        return self.category == self.Category.T2V

    def is_available_for_i2v(self):
        """Check if model is available for Image-to-Video"""
        return self.category == self.Category.I2V

    def get_max_duration(self):
        """Returns maximum duration for this model"""
        return self.max_duration

    def get_max_resolution(self):
        """Returns maximum resolution as string (e.g., '1920x1080')"""
        resolutions = self.get_available_resolutions()
        if not resolutions:
            return '1920x1080'
        # Return the highest resolution
        return resolutions[-1] if resolutions else '1920x1080'

    def get_category_display_name(self):
        """Returns human-readable category name"""
        if self.supports_image_to_video:
            return "Image-to-Video"
        # Use Django's built-in get_FOO_display() method
        return dict(self.Category.choices).get(self.category, self.category)

    def get_available_resolutions(self):
        """Returns list of available resolutions"""
        resolutions = []
        resolution_fields = [
            ('512x512', self.resolution_512x512),
            ('512x768', self.resolution_512x768),
            ('512x1024', self.resolution_512x1024),
            ('768x512', self.resolution_768x512),
            ('768x768', self.resolution_768x768),
            ('768x1024', self.resolution_768x1024),
            ('1024x512', self.resolution_1024x512),
            ('1024x768', self.resolution_1024x768),
            ('1024x1024', self.resolution_1024x1024),
            ('1280x720', self.resolution_1280x720),
            ('1920x1080', self.resolution_1920x1080),
            ('2560x1440', self.resolution_2560x1440),
            ('3840x2160', self.resolution_3840x2160),
        ]
        for res, enabled in resolution_fields:
            if enabled:
                resolutions.append(res)
        return resolutions

    def get_available_aspect_ratios(self):
        """Returns list of available aspect ratios"""
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

    def get_available_durations(self):
        """Returns list of available durations"""
        durations = []
        duration_fields = [
            (2, self.duration_2),
            (3, self.duration_3),
            (4, self.duration_4),
            (5, self.duration_5),
            (6, self.duration_6),
            (8, self.duration_8),
            (10, self.duration_10),
            (12, self.duration_12),
            (15, self.duration_15),
            (20, self.duration_20),
            (30, self.duration_30),
        ]
        for duration, enabled in duration_fields:
            if enabled:
                durations.append(duration)
        return durations

    def get_available_fps(self):
        """
        Returns list of discrete FPS values allowed for this model,
        based on the checkbox selections (fps_15, fps_24, fps_30, fps_60, fps_90, fps_120).
        """
        if not self.supports_fps:
            return []

        fps_values = []
        fps_fields = [
            (15, self.fps_15),
            (24, self.fps_24),
            (30, self.fps_30),
            (60, self.fps_60),
            (90, self.fps_90),
            (120, self.fps_120),
        ]
        for fps, enabled in fps_fields:
            if enabled:
                fps_values.append(fps)

        # Если ничего не выбрано, но default_fps валиден — хотя бы его вернём
        if not fps_values and self.default_fps in VALID_FPS:
            fps_values = [self.default_fps]

        return fps_values

    def get_available_camera_movements(self):
        """Returns list of available camera movements"""
        if not self.supports_camera_movement:
            return []

        movements = []
        movement_fields = [
            ('static', 'Статичная', self.camera_static),
            ('pan_left', 'Панорама влево', self.camera_pan_left),
            ('pan_right', 'Панорама вправо', self.camera_pan_right),
            ('tilt_up', 'Наклон вверх', self.camera_tilt_up),
            ('tilt_down', 'Наклон вниз', self.camera_tilt_down),
            ('zoom_in', 'Приближение', self.camera_zoom_in),
            ('zoom_out', 'Отдаление', self.camera_zoom_out),
            ('dolly_in', 'Движение вперёд', self.camera_dolly_in),
            ('dolly_out', 'Движение назад', self.camera_dolly_out),
            ('orbit_left', 'Орбита влево', self.camera_orbit_left),
            ('orbit_right', 'Орбита вправо', self.camera_orbit_right),
            ('crane_up', 'Кран вверх', self.camera_crane_up),
            ('crane_down', 'Кран вниз', self.camera_crane_down),
        ]
        for value, label, enabled in movement_fields:
            if enabled:
                movements.append({'value': value, 'label': label})
        return movements

    def get_available_quality_levels(self):
        """Returns list of available quality levels"""
        if not self.supports_quality:
            return []

        qualities = []
        quality_fields = [
            ('low', 'Низкое', self.quality_low),
            ('medium', 'Среднее', self.quality_medium),
            ('high', 'Высокое', self.quality_high),
            ('ultra', 'Ультра', self.quality_ultra),
        ]
        for value, label, enabled in quality_fields:
            if enabled:
                qualities.append({'value': value, 'label': label})
        return qualities

    def get_available_styles(self):
        """Returns list of available style presets"""
        if not self.supports_style_presets:
            return []

        styles = []
        style_fields = [
            ('realistic', 'Реалистичный', self.style_realistic),
            ('anime', 'Аниме', self.style_anime),
            ('cartoon', 'Мультяшный', self.style_cartoon),
            ('cinematic', 'Кинематографичный', self.style_cinematic),
            ('artistic', 'Художественный', self.style_artistic),
        ]
        for value, label, enabled in style_fields:
            if enabled:
                styles.append({'value': value, 'label': label})
        return styles

    def get_configuration_summary(self):
        """Returns a summary of the model configuration for JavaScript"""
        config = {
            'model_id': self.model_id,
            'name': self.name,
            'category': self.category,
            'is_t2v': self.is_available_for_t2v(),
            'is_i2v': self.is_available_for_i2v(),
            'token_cost': self.token_cost,
        }

        # Only include parameters that are enabled
        if self.get_available_resolutions():
            config['resolutions'] = self.get_available_resolutions()

        if self.get_available_aspect_ratios():
            config['aspect_ratios'] = self.get_available_aspect_ratios()

        if self.get_available_durations():
            config['durations'] = self.get_available_durations()

        if self.supports_camera_movement and self.get_available_camera_movements():
            config['camera_movements'] = self.get_available_camera_movements()

        if self.supports_quality and self.get_available_quality_levels():
            config['quality_levels'] = self.get_available_quality_levels()

        if self.supports_style_presets and self.get_available_styles():
            config['styles'] = self.get_available_styles()

        if self.supports_image_to_video and self.supports_motion_strength:
            config['motion_strength'] = {
                'min': self.min_motion_strength,
                'max': self.max_motion_strength,
                'default': self.default_motion_strength
            }

        if self.supports_seed:
            config['supports_seed'] = True

        if self.supports_negative_prompt:
            config['supports_negative_prompt'] = True

        if self.supports_fps:
            config['fps'] = {
                'min': self.min_fps,
                'max': self.max_fps,
                'default': self.default_fps
            }

        if self.supports_guidance_scale:
            config['guidance_scale'] = {
                'min': self.min_guidance_scale,
                'max': self.max_guidance_scale,
                'default': self.default_guidance_scale
            }

        if self.supports_inference_steps:
            config['inference_steps'] = {
                'min': self.min_inference_steps,
                'max': self.max_inference_steps,
                'default': self.default_inference_steps
            }

        if self.supports_multiple_videos:
            config['multiple_videos'] = {
                'min': self.min_videos or 1,
                'max': self.max_videos or 4,
                'default': self.default_videos or 1
            }

        return config
