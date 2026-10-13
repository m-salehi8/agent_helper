from rest_framework import serializers
from agent_helper.models import AssistantConversation, AssistantMessage, PendingAction


class ChatRequestSerializer(serializers.Serializer):
    """سریالایزر درخواست ارسال پیام چت"""
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(required=True, allow_blank=False, max_length=5000)
    image = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=8_000_000)


class AssistantMessageSerializer(serializers.ModelSerializer):
    """سریالایزر پیام‌های دستیار"""
    class Meta:
        model = AssistantMessage
        fields = ['id', 'role', 'content', 'created_at']


class AssistantConversationSerializer(serializers.ModelSerializer):
    """سریالایزر تاریخچه نشست‌های گفتگو"""
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = AssistantConversation
        fields = ['id', 'title', 'created_at', 'messages_count']


class AssistantConversationDetailSerializer(serializers.ModelSerializer):
    """سریالایزر جزئیات نشست گفتگو همراه با پیام‌ها"""
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantConversation
        fields = ['id', 'title', 'created_at', 'messages']


class PendingActionSerializer(serializers.ModelSerializer):
    """سریالایزر اقدامات پیشنهادی معلق"""
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PendingAction
        fields = [
            'id', 'conversation_id', 'kind', 'payload',
            'status', 'created_at', 'expires_at', 'executed_at',
            'result', 'is_expired'
        ]
