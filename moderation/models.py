from django.db import models
from django.conf import settings


class Report(models.Model):
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('inappropriate', 'Неподходящий контент'),
        ('copyright', 'Нарушение авторских прав'),
        ('fake', 'Ложная информация'),
        ('other', 'Другое')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        db_index=True
    )
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, db_index=True)
    details = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'

    def __str__(self):
        return f"Report #{self.pk} - {self.get_reason_display()}"


class ModerationFlag(models.Model):
    """
    Простая модерация: можно заблокировать job или public_photo.
    """
    job = models.ForeignKey(
        "generate.GenerationJob",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="moderation_flags",
        db_index=True,
    )
    public_photo = models.ForeignKey(
        "gallery.PublicPhoto",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="moderation_flags",
        db_index=True,
    )
    is_blocked = models.BooleanField(default=False, db_index=True)
    reason = models.CharField(max_length=240, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        tgt = self.job_id or self.public_photo_id
        return f"ModerationFlag({tgt} blocked={self.is_blocked})"
