# websocket consumer for real-time chat functionality
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Conversation, Message
from .services.llm import LLMService


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        # only accept if user is authenticated
        if self.user.is_authenticated:
            # join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # receive message from websocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        if self.user.is_authenticated:
            # save user message to database
            user_message = await self.save_message(self.user, message, 'user')
            
            # send user message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'role': 'user',
                    'message_id': user_message.id,
                    'timestamp': user_message.timestamp.isoformat()
                }
            )

            # get ai response
            try:
                llm_service = LLMService()
                ai_response = await database_sync_to_async(llm_service.get_response)(
                    message=message,
                    user=self.user
                )

                # save ai response to database
                ai_message = await self.save_message(self.user, ai_response, 'assistant')

                # send ai response to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': ai_response,
                        'role': 'assistant',
                        'message_id': ai_message.id,
                        'timestamp': ai_message.timestamp.isoformat()
                    }
                )

            except Exception as e:
                # send error message
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': f'Sorry, I encountered an error: {str(e)}',
                        'role': 'assistant',
                        'error': True
                    }
                )

    # receive message from room group
    async def chat_message(self, event):
        # send message to websocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'role': event['role'],
            'message_id': event.get('message_id'),
            'timestamp': event.get('timestamp'),
            'error': event.get('error', False)
        }))

    @database_sync_to_async
    def save_message(self, user, content, role):
        conversation = Conversation.objects.get(id=self.conversation_id, user=user)
        message = Message.objects.create(
            conversation=conversation,
            role=role,
            content=content
        )
        # Update conversation timestamp
        conversation.save()
        return message