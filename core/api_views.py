# django rest framework api views for chat functionality
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer, 
    ConversationListSerializer, 
    MessageSerializer,
    MessageCreateSerializer
)
from .services.llm import LLMService


# list user's conversations or create new conversation
class ConversationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ConversationListSerializer
        return ConversationSerializer
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # create conversation with auto-generated title
        title = serializer.validated_data.get('title', f"Chat {timezone.now().strftime('%b %d, %Y')}")
        serializer.save(user=self.request.user, title=title)


# get specific conversation with all messages
class ConversationDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        # add logging for delete operations
        conversation_id = kwargs.get('pk')
        print(f"Delete request for conversation {conversation_id} by user {request.user}")
        return super().destroy(request, *args, **kwargs)


# send message to conversation and get ai response
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    serializer = MessageCreateSerializer(data=request.data)
    if serializer.is_valid():
        # save user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=serializer.validated_data['content']
        )
        
        # get ai response
        try:
            llm_service = LLMService()
            ai_response = llm_service.get_response(
                message=user_message.content,
                user=request.user
            )
            
            # save ai response
            ai_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response
            )
            
            # update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()
            
            return Response({
                'user_message': MessageSerializer(user_message).data,
                'ai_message': MessageSerializer(ai_message).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get AI response: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# get messages for a specific conversation
class ConversationMessagesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id, user=self.request.user)
        return conversation.messages.all()


# update conversation title
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_conversation_title(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    title = request.data.get('title')
    if title:
        conversation.title = title
        conversation.save()
        return Response({'title': conversation.title})
    
    return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)