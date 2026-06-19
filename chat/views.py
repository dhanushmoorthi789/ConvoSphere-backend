from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import Conversation, ConversationParticipant, Message, MessageReaction, MessageStatus
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageReactionSerializer
)

User = get_user_model()


class ConversationListCreateView(APIView):
    """List all conversations or create a new one"""

    def get(self, request):
        conversations = Conversation.objects.filter(
            participants=request.user, is_active=True
        ).prefetch_related('participants', 'messages')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        participant_ids = data['participant_ids']
        conv_type = data['type']

        # Validate participants exist
        participants = User.objects.filter(id__in=participant_ids, is_active=True)
        if participants.count() != len(participant_ids):
            return Response({'error': 'One or more users not found.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # For direct chats, check if one already exists
            if conv_type == 'direct':
                if len(participant_ids) != 1:
                    return Response({'error': 'Direct chat requires exactly one other participant.'}, status=status.HTTP_400_BAD_REQUEST)

                other_user = participants.first()
                existing = Conversation.objects.filter(
                    type='direct', participants=request.user
                ).filter(participants=other_user)

                if existing.exists():
                    conv = existing.first()
                    return Response(ConversationSerializer(conv, context={'request': request}).data)

            # Create new conversation
            conv = Conversation.objects.create(
                type=conv_type,
                name=data.get('name', ''),
                description=data.get('description', ''),
                created_by=request.user
            )

            # Add creator as admin
            ConversationParticipant.objects.create(conversation=conv, user=request.user, role='admin')

            # Add other participants
            for user in participants:
                ConversationParticipant.objects.create(conversation=conv, user=user, role='member')

        return Response(ConversationSerializer(conv, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """Get, update, or delete a specific conversation"""

    def get_conversation(self, request, conv_id):
        try:
            conv = Conversation.objects.get(id=conv_id, participants=request.user, is_active=True)
            return conv
        except Conversation.DoesNotExist:
            return None

    def get(self, request, conv_id):
        conv = self.get_conversation(request, conv_id)
        if not conv:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ConversationSerializer(conv, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, conv_id):
        conv = self.get_conversation(request, conv_id)
        if not conv:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Only admin or creator can update
        participant = ConversationParticipant.objects.filter(conversation=conv, user=request.user).first()
        if not participant or participant.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        allowed_fields = ['name', 'description', 'avatar']
        for field in allowed_fields:
            if field in request.data:
                setattr(conv, field, request.data[field])
        conv.save()
        return Response(ConversationSerializer(conv, context={'request': request}).data)

    def delete(self, request, conv_id):
        conv = self.get_conversation(request, conv_id)
        if not conv:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        conv.is_active = False
        conv.save()
        return Response({'message': 'Conversation deleted.'}, status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(APIView):
    """List messages in a conversation or send a new message"""
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, conv_id):
        try:
            conv = Conversation.objects.get(id=conv_id, participants=request.user, is_active=True)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(
            conversation=conv
        ).select_related('sender', 'reply_to').prefetch_related('reactions')

        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 50))
        offset = (page - 1) * limit
        total = messages.count()
        messages = messages[offset:offset + limit]

        # Mark messages as read
        participant = ConversationParticipant.objects.filter(conversation=conv, user=request.user).first()
        if participant:
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])

        serializer = MessageSerializer(messages, many=True)
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'has_more': offset + limit < total
        })

    def post(self, request, conv_id):
        try:
            conv = Conversation.objects.get(id=conv_id, participants=request.user, is_active=True)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['conversation'] = conv_id

        # Determine message type if file is uploaded
        if 'image' in request.FILES:
            data['message_type'] = 'image'
        elif 'file' in request.FILES:
            file = request.FILES['file']
            mime = file.content_type
            if mime.startswith('video/'):
                data['message_type'] = 'video'
            elif mime.startswith('audio/'):
                data['message_type'] = 'audio'
            else:
                data['message_type'] = 'document' if 'pdf' in mime or 'doc' in mime or 'sheet' in mime else 'file'
            data['file_name'] = file.name
            data['file_size'] = file.size

        serializer = MessageCreateSerializer(data=data)
        if serializer.is_valid():
            message = serializer.save(sender=request.user)
            conv.updated_at = timezone.now()
            conv.save(update_fields=['updated_at'])
            return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageDetailView(APIView):
    """Get, update, or delete a specific message"""

    def get_message(self, request, msg_id):
        try:
            return Message.objects.get(id=msg_id, conversation__participants=request.user)
        except Message.DoesNotExist:
            return None

    def get(self, request, msg_id):
        msg = self.get_message(request, msg_id)
        if not msg:
            return Response({'error': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(MessageSerializer(msg).data)

    def patch(self, request, msg_id):
        msg = self.get_message(request, msg_id)
        if not msg:
            return Response({'error': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)
        if msg.sender != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        new_content = request.data.get('content')
        if new_content:
            msg.content = new_content
            msg.is_edited = True
            msg.save(update_fields=['content', 'is_edited', 'updated_at'])
        return Response(MessageSerializer(msg).data)

    def delete(self, request, msg_id):
        msg = self.get_message(request, msg_id)
        if not msg:
            return Response({'error': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)
        if msg.sender != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        msg.is_deleted = True
        msg.content = ''
        msg.save(update_fields=['is_deleted', 'content'])
        return Response({'message': 'Message deleted.'}, status=status.HTTP_204_NO_CONTENT)


class MessageReactionView(APIView):
    """Add or remove a reaction on a message"""

    def post(self, request, msg_id):
        try:
            msg = Message.objects.get(id=msg_id, conversation__participants=request.user)
        except Message.DoesNotExist:
            return Response({'error': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        emoji = request.data.get('emoji')
        if not emoji:
            return Response({'error': 'Emoji is required.'}, status=status.HTTP_400_BAD_REQUEST)

        reaction, created = MessageReaction.objects.get_or_create(
            message=msg, user=request.user, emoji=emoji
        )
        if not created:
            reaction.delete()
            return Response({'message': 'Reaction removed.'})
        return Response(MessageReactionSerializer(reaction).data, status=status.HTTP_201_CREATED)


class ConversationParticipantView(APIView):
    """Add or remove participants from a group conversation"""

    def post(self, request, conv_id):
        """Add a participant"""
        try:
            conv = Conversation.objects.get(id=conv_id, participants=request.user, is_active=True, type='group')
        except Conversation.DoesNotExist:
            return Response({'error': 'Group conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        participant, created = ConversationParticipant.objects.get_or_create(
            conversation=conv, user=user, defaults={'role': 'member'}
        )
        if not created:
            return Response({'error': 'User is already in this conversation.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f'{user.username} added to conversation.'})

    def delete(self, request, conv_id):
        """Remove a participant"""
        try:
            conv = Conversation.objects.get(id=conv_id, participants=request.user, is_active=True, type='group')
        except Conversation.DoesNotExist:
            return Response({'error': 'Group conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        ConversationParticipant.objects.filter(conversation=conv, user_id=user_id).delete()
        return Response({'message': 'Participant removed.'})


class MarkReadView(APIView):
    """Mark all messages in a conversation as read"""

    def post(self, request, conv_id):
        participant = ConversationParticipant.objects.filter(
            conversation_id=conv_id, user=request.user
        ).first()
        if participant:
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])
        return Response({'message': 'Messages marked as read.'})
