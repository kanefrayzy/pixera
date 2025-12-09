"""
Reference Images for Generation Jobs
Allows users to upload up to 5 reference images for any generation (image or video)
"""
from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator


class ReferenceImage(models.Model):
    """
    Reference image attached to a generation job.
    Users can upload up to 5 reference images to guide the generation.
    """
    job = models.ForeignKey(
        'GenerationJob',
        on_delete=models.CASCADE,
        related_name='reference_images',
        verbose_name='Задача генерации'
    )

    image = models.ImageField(
        upload_to='references/%Y/%m/',
        verbose_name='Референсное изображение',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp']
            )
        ]
    )

    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name='Порядок'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Загружено'
    )

    # Optional: influence weight for this reference (0.0 - 1.0)
    influence_weight = models.FloatField(
        default=1.0,
        verbose_name='Вес влияния',
        help_text='Сила влияния этого референса (0.0 - 1.0)'
    )

    class Meta:
        ordering = ('order', 'uploaded_at')
        verbose_name = 'Референсное изображение'
        verbose_name_plural = 'Референсные изображения'
        indexes = [
            models.Index(fields=['job', 'order']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(influence_weight__gte=0.0) & models.Q(influence_weight__lte=1.0),
                name='reference_image_influence_weight_range'
            )
        ]

    def __str__(self):
        return f"Reference #{self.order + 1} for Job #{self.job_id}"

    @property
    def thumbnail_url(self):
        """Returns URL for thumbnail (can be optimized later)"""
        if self.image:
            return self.image.url
        return None
