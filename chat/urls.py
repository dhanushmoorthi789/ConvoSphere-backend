from django.urls import path
from . import views

urlpatterns = [
    # Conversations
    path('conversations/', views.ConversationListCreateView.as_view(), name='conversations'),
    path('conversations/<int:conv_id>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conv_id>/messages/', views.MessageListCreateView.as_view(), name='messages'),
    path('conversations/<int:conv_id>/participants/', views.ConversationParticipantView.as_view(), name='participants'),
    path('conversations/<int:conv_id>/read/', views.MarkReadView.as_view(), name='mark-read'),
    # Messages
    path('messages/<int:msg_id>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:msg_id>/react/', views.MessageReactionView.as_view(), name='message-react'),
]
