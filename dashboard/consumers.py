"""
WebSocket consumer for real-time notifications
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope.get("user")

        # Only allow authenticated users
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Create a unique group name for this user
        self.group_name = f"notifications_{self.user.id}"

        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to notification stream"
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle messages from WebSocket (ping/pong for keepalive)"""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({
                    "type": "pong"
                }))
        except Exception:
            pass

    async def notification_message(self, event):
        """Handle notification messages sent to the group"""
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            "type": "new_notification",
            "notification": event["notification"]
        }))
