import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message, UserProfile

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Mark user as online
        await self.set_user_online(True)

    async def disconnect(self, close_code):
        # Mark user as offline
        await self.set_user_online(False)

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')

            if message_type == 'chat_message':
                message = data['message']
                username = data['username']

                # Save message to database
                msg = await self.save_message(username, message)

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'username': username,
                        'timestamp': msg['timestamp'],
                        'message_id': msg['id']
                    }
                )
            
            elif message_type == 'typing':
                # Broadcast typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'username': data['username'],
                        'is_typing': data['is_typing']
                    }
                )
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))

    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def save_message(self, username, message):
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(id=self.room_id)
            msg = Message.objects.create(
                room=room,
                sender=user,
                content=message
            )
            return {
                'id': msg.id,
                'timestamp': msg.timestamp.strftime('%H:%M')
            }
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    @database_sync_to_async
    def set_user_online(self, status):
        try:
            user = self.scope['user']
            if user.is_authenticated:
                # FIXED: Changed from user.profile.get_or_create to UserProfile.objects.get_or_create
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.online = status
                profile.save(update_fields=['online'])
        except Exception as e:
            logger.error(f"Error setting user online status: {e}")