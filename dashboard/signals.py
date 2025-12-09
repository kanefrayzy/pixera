"""
Signal handlers for sending real-time notifications
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification


@receiver(post_save, sender=Notification)
def send_notification_to_websocket(sender, instance, created, **kwargs):
    """
    Send notification to user's WebSocket channel when a new notification is created
    """
    if not created:
        return

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        # Get actor info
        actor_info = {"username": "", "avatar_url": ""}
        if instance.actor:
            try:
                prof = getattr(instance.actor, "profile", None)
                avatar_url = getattr(getattr(prof, "avatar", None), "url", "") if prof else ""
            except Exception:
                avatar_url = ""
            actor_info = {
                "username": instance.actor.username,
                "avatar_url": avatar_url
            }

        # Prepare notification data
        notification_data = {
            "id": instance.id,
            "type": instance.type,
            "message": instance.message,
            "link": instance.link,
            "is_read": instance.is_read,
            "created_at": instance.created_at.isoformat(),
            "actor": actor_info,
            "preview": {
                "kind": None,
                "image_url": "",
                "video_url": "",
                "poster_url": "",
                "text": "",
            },
        }

        # Send to user's notification group
        group_name = f"notifications_{instance.recipient_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification_message",
                "notification": notification_data
            }
        )
    except Exception as e:
        # Don't break notification creation if WebSocket fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send notification to WebSocket: {e}")
