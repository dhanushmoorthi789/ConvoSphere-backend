from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, ConversationParticipant, Message, MessageReaction, MessageStatus

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar_url', 'is_online', 'last_seen', 'status_message']


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'emoji', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    file_url = serializers.ReadOnlyField()
    image_url = serializers.ReadOnlyField()
    reply_to_preview = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'file', 'image', 'file_url', 'image_url', 'file_name', 'file_size',
            'reply_to', 'reply_to_preview', 'is_deleted', 'is_edited',
            'reactions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']

    def get_reply_to_preview(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender': obj.reply_to.sender.username if obj.reply_to.sender else 'Unknown',
                'content': obj.reply_to.content[:100] if obj.reply_to.content else '[file]',
                'message_type': obj.reply_to.message_type,
            }
        return None


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['conversation', 'message_type', 'content', 'file', 'image', 'file_name', 'file_size', 'reply_to']


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user', 'role', 'joined_at', 'last_read_at', 'is_muted']


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(
        source='conversationparticipant_set', many=True, read_only=True
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'description', 'avatar',
            'participants', 'created_by', 'created_at', 'updated_at',
            'is_active', 'last_message', 'unread_count', 'other_user'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.get_last_message()
        if msg:
            return {
                'id': msg.id,
                'content': msg.content if not msg.is_deleted else '🚫 Message deleted',
                'message_type': msg.message_type,
                'sender_name': msg.sender.username if msg.sender else 'Unknown',
                'created_at': msg.created_at,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_user(self, obj):
        """For direct chats, return the other participant's info"""
        if obj.type == 'direct':
            request = self.context.get('request')
            if request:
                other = obj.participants.exclude(id=request.user.id).first()
                if other:
                    return UserBasicSerializer(other).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['direct', 'group'])
    participant_ids = serializers.ListField(child=serializers.IntegerField())
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
