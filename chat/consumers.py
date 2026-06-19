# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.contrib.auth import get_user_model
# from django.utils import timezone

# User = get_user_model()




# class ChatConsumer(AsyncWebsocketConsumer):
#     """WebSocket consumer for real-time chat"""

#     async def connect(self):
#         self.user = self.scope.get('user')
#         if not self.user or not self.user.is_authenticated:
#             await self.close()
#             return

#         self.conv_id = self.scope['url_route']['kwargs']['conv_id']
#         self.room_group_name = f'chat_{self.conv_id}'

#         # Join the room group
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#         await self.accept()

#         # Mark user as online
#         await self.set_user_online(True)

#         # Notify others user joined
#         await self.channel_layer.group_send(self.room_group_name, {
#             'type': 'user_status',
#             'user_id': self.user.id,
#             'username': self.user.username,
#             'is_online': True,
#         })

#     async def disconnect(self, close_code):
#         if hasattr(self, 'room_group_name'):
#             await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#         if hasattr(self, 'user') and self.user.is_authenticated:
#             await self.set_user_online(False)
#             if hasattr(self, 'room_group_name'):
#                 await self.channel_layer.group_send(self.room_group_name, {
#                     'type': 'user_status',
#                     'user_id': self.user.id,
#                     'username': self.user.username,
#                     'is_online': False,
#                 })

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#             event_type = data.get('type')

#             if event_type == 'message':
#                 await self.handle_message(data)
#             elif event_type == 'typing':
#                 await self.handle_typing(data)
#             elif event_type == 'read':
#                 await self.handle_read(data)
#         except json.JSONDecodeError:
#             pass

#     async def handle_message(self, data):
#         """Broadcast a new message to the group"""
#         await self.channel_layer.group_send(self.room_group_name, {
#             'type': 'chat_message',
#             'message': data.get('message'),
#         })

#     async def handle_typing(self, data):
#         """Broadcast typing indicator"""
#         await self.channel_layer.group_send(self.room_group_name, {
#             'type': 'typing_indicator',
#             'user_id': self.user.id,
#             'username': self.user.username,
#             'is_typing': data.get('is_typing', False),
#         })

#     async def handle_read(self, data):
#         """Broadcast read receipt"""
#         await self.channel_layer.group_send(self.room_group_name, {
#             'type': 'read_receipt',
#             'user_id': self.user.id,
#             'message_id': data.get('message_id'),
#         })

#     # Event handlers (called by channel layer)
#     async def chat_message(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'message',
#             'message': event['message'],
#         }))

#     async def typing_indicator(self, event):
#         if event['user_id'] != self.user.id:
#             await self.send(text_data=json.dumps({
#                 'type': 'typing',
#                 'user_id': event['user_id'],
#                 'username': event['username'],
#                 'is_typing': event['is_typing'],
#             }))

#     async def user_status(self, event):
#         if event['user_id'] != self.user.id:
#             await self.send(text_data=json.dumps({
#                 'type': 'user_status',
#                 'user_id': event['user_id'],
#                 'username': event['username'],
#                 'is_online': event['is_online'],
#             }))

#     async def read_receipt(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'read',
#             'user_id': event['user_id'],
#             'message_id': event['message_id'],
#         }))

#     @database_sync_to_async
#     def set_user_online(self, is_online):
#         User.objects.filter(id=self.user.id).update(
#             is_online=is_online,
#             last_seen=timezone.now()
#         )



import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.room_group_name = f'chat_{self.conv_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.set_user_online(True)

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_status',
            'user_id': self.user.id,
            'username': self.user.username,
            'is_online': True,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.set_user_online(False)

            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': False,
                })

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get('type')

            if event_type == 'message':
                await self.handle_message(data)
            elif event_type == 'typing':
                await self.handle_typing(data)
            elif event_type == 'read':
                await self.handle_read(data)

        except json.JSONDecodeError:
            pass

    async def handle_message(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'chat_message',
            'message': data.get('message'),
        })

    async def handle_typing(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'typing_indicator',
            'user_id': self.user.id,
            'username': self.user.username,
            'is_typing': data.get('is_typing', False),
        })

    async def handle_read(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'read_receipt',
            'user_id': self.user.id,
            'message_id': data.get('message_id'),
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def user_status(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_online': event['is_online'],
            }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read',
            'user_id': event['user_id'],
            'message_id': event['message_id'],
        }))

    @database_sync_to_async
    def set_user_online(self, is_online):
        User = get_user_model()   # ✅ moved here

        User.objects.filter(id=self.user.id).update(
            is_online=is_online,
            last_seen=timezone.now()
        )