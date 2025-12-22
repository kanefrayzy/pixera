"""
Aspect Ratio Quality Configurations
Система для хранения точных размеров для каждой комбинации соотношения сторон и качества
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class AspectRatioQualityConfig(models.Model):
    """
    Конфигурация размеров для комбинации соотношения сторон + качество
    Администратор создает записи для каждой поддерживаемой модел ью комбинации
    """
    
    class QualityLevel(models.TextChoices):
        SD = 'sd', 'SD (480p)'
        HD = 'hd', 'HD (720p)'
        FULL_HD = 'full_hd', 'Full HD (1080p)'
        QHD = '2k', '2K (1440p)'
        UHD = '4k', '4K (2160p)'
        UHD_8K = '8k', '8K (4320p)'
    
    # Связь с моделью (через ContentType для универсальности)
    model_type = models.CharField(
        "Тип модели",
        max_length=20,
        choices=[('image', 'Фото'), ('video', 'Видео')],
        db_index=True
    )
    
    model_id = models.PositiveIntegerField(
        "ID модели",
        db_index=True,
        help_text="ID ImageModelConfiguration или VideoModelConfiguration"
    )
    
    # Соотношение сторон
    aspect_ratio = models.CharField(
        "Соотношение сторон",
        max_length=20,
        db_index=True,
        help_text="Например: 1:1, 16:9, 9:16, 4:5, 21:9"
    )
    
    # Качество
    quality = models.CharField(
        "Качество",
        max_length=20,
        choices=QualityLevel.choices,
        db_index=True
    )
    
    # Точные размеры (проверенные на Runware)
    width = models.PositiveIntegerField(
        "Ширина (px)",
        validators=[MinValueValidator(64), MaxValueValidator(8192)],
        help_text="Точная ширина в пикселях (проверено на Runware)"
    )
    
    height = models.PositiveIntegerField(
        "Высота (px)",
        validators=[MinValueValidator(64), MaxValueValidator(8192)],
        help_text="Точная высота в пикселях (проверено на Runware)"
    )
    
    # Метаданные
    is_active = models.BooleanField(
        "Активно",
        default=True,
        db_index=True
    )
    
    is_default = models.BooleanField(
        "По умолчанию",
        default=False,
        help_text="Использовать эту комбинацию по умолчанию для модели"
    )
    
    order = models.PositiveIntegerField(
        "Порядок отображения",
        default=0,
        help_text="Меньше = выше в списке"
    )
    
    notes = models.TextField(
        "Заметки",
        blank=True,
        help_text="Внутренние заметки (результаты тестов на Runware, особенности и т.д.)"
    )
    
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    
    class Meta:
        verbose_name = "Конфигурация соотношения и качества"
        verbose_name_plural = "Конфигурации соотношений и качества"
        ordering = ['model_type', 'model_id', 'order', 'aspect_ratio', 'quality']
        unique_together = [['model_type', 'model_id', 'aspect_ratio', 'quality']]
        indexes = [
            models.Index(fields=['model_type', 'model_id', 'is_active']),
            models.Index(fields=['aspect_ratio', 'quality']),
        ]
    
    def __str__(self):
        return f"{self.aspect_ratio} @ {self.get_quality_display()} = {self.width}×{self.height}"
    
    @property
    def resolution_string(self):
        """Возвращает строку разрешения для передачи в API"""
        return f"{self.width}x{self.height}"
    
    @property
    def megapixels(self):
        """Вычисляет мегапиксели"""
        return round((self.width * self.height) / 1_000_000, 2)
    
    def get_aspect_ratio_decimal(self):
        """Вычисляет десятичное соотношение"""
        try:
            parts = self.aspect_ratio.replace(':', '/').split('/')
            if len(parts) == 2:
                return float(parts[0]) / float(parts[1])
        except:
            pass
        return None
    
    def validate_dimensions(self):
        """Проверяет, что размеры соответствуют заявленному соотношению сторон"""
        ratio_decimal = self.get_aspect_ratio_decimal()
        if ratio_decimal:
            actual_ratio = self.width / self.height
            # Допускаем погрешность 1%
            return abs(actual_ratio - ratio_decimal) / ratio_decimal < 0.01
        return True
    
    def save(self, *args, **kwargs):
        # Если установлен флаг по умолчанию, сбрасываем его у других конфигураций
        if self.is_default:
            AspectRatioQualityConfig.objects.filter(
                model_type=self.model_type,
                model_id=self.model_id,
                is_default=True
            ).update(is_default=False)
        
        super().save(*args, **kwargs)


class AspectRatioPreset(models.Model):
    """
    Предустановки соотношений сторон для быстрого добавления
    """
    
    name = models.CharField(
        "Название",
        max_length=100,
        help_text="Описательное название (например: 'Instagram Stories')"
    )
    
    aspect_ratio = models.CharField(
        "Соотношение",
        max_length=20,
        unique=True
    )
    
    category = models.CharField(
        "Категория",
        max_length=50,
        blank=True,
        help_text="Группировка (соцсети, кино, фото и т.д.)"
    )
    
    icon = models.CharField(
        "Иконка",
        max_length=10,
        blank=True,
        help_text="Emoji иконка для отображения"
    )
    
    description = models.TextField(
        "Описание",
        blank=True,
        help_text="Где используется это соотношение"
    )
    
    # Рекомендуемые размеры для разных качеств
    recommended_sd = models.CharField("SD рекомендация", max_length=20, blank=True, help_text="Например: 640x480")
    recommended_hd = models.CharField("HD рекомендация", max_length=20, blank=True, help_text="Например: 1280x720")
    recommended_full_hd = models.CharField("Full HD рекомендация", max_length=20, blank=True, help_text="Например: 1920x1080")
    recommended_2k = models.CharField("2K рекомендация", max_length=20, blank=True, help_text="Например: 2560x1440")
    recommended_4k = models.CharField("4K рекомендация", max_length=20, blank=True, help_text="Например: 3840x2160")
    recommended_8k = models.CharField("8K рекомендация", max_length=20, blank=True, help_text="Например: 7680x4320")
    
    is_common = models.BooleanField(
        "Популярное",
        default=False,
        help_text="Часто используемое соотношение"
    )
    
    order = models.PositiveIntegerField("Порядок", default=0)
    
    class Meta:
        verbose_name = "Предустановка соотношения сторон"
        verbose_name_plural = "Предустановки соотношений сторон"
        ordering = ['-is_common', 'order', 'aspect_ratio']
    
    def __str__(self):
        if self.name:
            return f"{self.aspect_ratio} ({self.name})"
        return self.aspect_ratio
    
    def get_recommended_size(self, quality):
        """Возвращает рекомендуемый размер для заданного качества"""
        mapping = {
            'sd': self.recommended_sd,
            'hd': self.recommended_hd,
            'full_hd': self.recommended_full_hd,
            '2k': self.recommended_2k,
            '4k': self.recommended_4k,
            '8k': self.recommended_8k,
        }
        return mapping.get(quality, '')
