# dashboard/models.py
from django.db import models
from django.conf import settings

STARTER_TOKENS = 0  # новый кошелёк = 0, чтобы «три гостевые обработки» не возвращались после входа

class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.PositiveIntegerField(default=STARTER_TOKENS)  # токены на руках
    purchased_total = models.PositiveIntegerField(default=0)       # всего куплено
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def charge(self, amount: int) -> bool:
        if amount <= 0:
            return True
        if self.balance < amount:
            return False
        self.balance -= amount
        self.save(update_fields=["balance", "updated_at"])
        return True

    def topup(self, amount: int):
        if amount <= 0:
            return
        self.balance += amount
        self.purchased_total += amount
        self.save(update_fields=["balance", "purchased_total", "updated_at"])

    def __str__(self):
        return f"Wallet({self.user_id}) = {self.balance}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_private = models.BooleanField(
        default=True,
        help_text="Если True, другие видят только опубликованные работы. Если False - все завершенные работы."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user_id})"


class Follow(models.Model):
    """
    Подписки между пользователями:
    - follower → кто подписался
    - following → на кого подписались
    Уникально по паре (follower, following).
    """
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_relations",
        db_index=True,
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers_relations",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = (("follower", "following"),)
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"Follow(u{self.follower_id} -> u{self.following_id})"


class Notification(models.Model):
    """
    Универсальные уведомления «как в инсте».
    - recipient: кому адресовано
    - actor: кто инициировал (может быть null, например для системных/рекомендаций/топ-апа)
    - type: тип события (enum)
    - message: короткий текст (i18n-friendly; безопасный)
    - link: ссылку, куда вести по клику
    - payload: доп.данные (ids, counters, thumbnails и т.д.)
    - is_read: прочитано/не прочитано
    """
    class Type(models.TextChoices):
        LIKE_PHOTO = "like_photo", "Like: photo"
        LIKE_VIDEO = "like_video", "Like: video"
        COMMENT_PHOTO = "comment_photo", "Comment: photo"
        COMMENT_VIDEO = "comment_video", "Comment: video"
        REPLY_PHOTO = "reply_photo", "Reply: photo comment"
        REPLY_VIDEO = "reply_video", "Reply: video comment"
        COMMENT_LIKE_PHOTO = "comment_like_photo", "Like: photo comment"
        COMMENT_LIKE_VIDEO = "comment_like_video", "Like: video comment"
        # Job (unpublished generation) interactions
        LIKE_JOB = "like_job", "Like: job"
        COMMENT_JOB = "comment_job", "Comment: job"
        REPLY_JOB = "reply_job", "Reply: job comment"
        COMMENT_LIKE_JOB = "comment_like_job", "Like: job comment"
        FOLLOW = "follow", "New follower"
        WALLET_TOPUP = "wallet_topup", "Wallet top-up"
        ADMIN_MESSAGE = "admin_message", "Admin message"
        RECOMMENDATION = "recommendation", "Recommendation"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_sent",
    )
    type = models.CharField(max_length=32, choices=Type.choices, db_index=True)
    message = models.CharField(max_length=200)
    link = models.CharField(max_length=300, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "type", "-created_at"]),
        ]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return f"Notif({self.type}) to u{self.recipient_id} by u{self.actor_id or '-'}"

    @classmethod
    def create(cls, *, recipient, actor=None, type: str, message: str, link: str = "", payload: dict | None = None):
        try:
            obj = cls.objects.create(
                recipient=recipient,
                actor=actor,
                type=type,
                message=message[:200],
                link=link[:300] if link else "",
                payload=payload or {},
            )
            return obj
        except Exception:
            # уведомления не должны «ронять» UX
            return None
