# celery tasks for background processing
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import Conversation, Message, User
from .services.llm import LLMService


@shared_task
def process_chat_message_async(conversation_id, user_id, message_content):
    """
    background task to process chat messages and stream responses
    """
    try:
        # get conversation and user
        conversation = Conversation.objects.get(id=conversation_id)
        user = User.objects.get(id=user_id)
        
        # save user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=message_content
        )
        
        # get ai response
        llm_service = LLMService()
        ai_response = llm_service.get_response(
            message=message_content,
            user=user
        )
        
        # save ai response
        ai_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_response
        )
        
        # send response via websocket
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation_id}'
        
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': ai_response,
                'role': 'assistant',
                'message_id': ai_message.id,
                'timestamp': ai_message.timestamp.isoformat()
            }
        )
        
        return {
            'success': True,
            'user_message_id': user_message.id,
            'ai_message_id': ai_message.id
        }
        
    except Exception as e:
        # send error message via websocket
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation_id}'
        
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': f'Sorry, I encountered an error: {str(e)}',
                'role': 'assistant',
                'error': True
            }
        )
        
        return {
            'success': False,
            'error': str(e)
        }