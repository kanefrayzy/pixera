from django.db import models


class ModerationFlag(models.Model):
    """
    Простая модерация: можно заблокировать job или public_photo.
    """
    job = models.ForeignKey(
        "generate.GenerationJob",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="moderation_flags",
    )
    public_photo = models.ForeignKey(
        "gallery.PublicPhoto",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="moderation_flags",
    )
    is_blocked = models.BooleanField(default=False, db_index=True)
    reason = models.CharField(max_length=240, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        tgt = self.job_id or self.public_photo_id
        return f"ModerationFlag({tgt} blocked={self.is_blocked})"
