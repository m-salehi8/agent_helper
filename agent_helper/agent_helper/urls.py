from django.urls import path

from agent_helper.views import (
    ActionCancelView,
    ActionConfirmView,
    ChatStreamView,
    ConversationDetailView,
    ConversationListView,
)

urlpatterns = [
    path('chat/', ChatStreamView.as_view(), name='assistant_chat'),
    path('conversations/', ConversationListView.as_view(), name='assistant_conversations'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='assistant_conversation_detail'),
    path('actions/<int:action_id>/confirm/', ActionConfirmView.as_view(), name='assistant_action_confirm'),
    path('actions/<int:action_id>/cancel/', ActionCancelView.as_view(), name='assistant_action_cancel'),
]
