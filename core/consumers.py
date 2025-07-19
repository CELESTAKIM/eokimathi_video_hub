# core/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.user_group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close() # Close connection if user is not authenticated

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    # Receive message from WebSocket (not used for this simple notification system)
    async def receive(self, text_data):
        pass

    # Receive message from channel layer (e.g., from a Django view)
    async def send_notification(self, event):
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': 'notification'
        }))