from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Conversation(models.Model):
    """Represents a chat conversation (direct or group)"""
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
    ]

    type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default='direct')
    name = models.CharField(max_length=100, blank=True)  # For group chats
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='group_avatars/', null=True, blank=True)
    participants = models.ManyToManyField(User, through='ConversationParticipant', related_name='conversations')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.type == 'group':
            return f"Group: {self.name}"
        return f"Direct: {self.id}"

    def get_last_message(self):
        return self.messages.filter(is_deleted=False).last()

    def get_unread_count(self, user):
        participant = self.conversationparticipant_set.filter(user=user).first()
        if participant:
            return self.messages.filter(
                created_at__gt=participant.last_read_at
            ).exclude(sender=user).count()
        return 0


class ConversationParticipant(models.Model):
    """Through model for conversation participants"""
    ROLES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(auto_now_add=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('conversation', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.conversation}"


class Message(models.Model):
    """Represents a single message in a conversation"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('file', 'File'),
        ('system', 'System Message'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='messages/files/', null=True, blank=True)
    image = models.ImageField(upload_to='messages/images/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_deleted = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.content[:50] if self.content else '[file]'}"

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return None


class MessageReaction(models.Model):
    """Emoji reactions on messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"{self.user.username}: {self.emoji} on msg {self.message.id}"


class MessageStatus(models.Model):
    """Read receipts for messages"""
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('message', 'user')
