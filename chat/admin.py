from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message, MessageReaction, MessageStatus

class ParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0
    readonly_fields = ['joined_at', 'last_read_at']

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['sender', 'message_type', 'content', 'is_deleted', 'created_at']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'name', 'created_by', 'created_at', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'created_by__email']
    inlines = [ParticipantInline, MessageInline]
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'is_deleted', 'is_edited', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'is_edited']
    search_fields = ['content', 'sender__email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'emoji', 'created_at']

@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'user', 'role', 'joined_at', 'is_muted']
    list_filter = ['role', 'is_muted']
