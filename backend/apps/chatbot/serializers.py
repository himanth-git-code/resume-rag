from rest_framework import serializers

from .models import EmployerChatMessage, EmployerChatSession


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerChatMessage
        fields = ["id", "role", "content", "status", "answer_status", "citations", "created_at"]


class AskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    session_id = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    turnstile_token = serializers.CharField(max_length=4096, required=False, allow_null=True, allow_blank=True)


class SessionSummarySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id")
    first_question = serializers.SerializerMethodField()

    class Meta:
        model = EmployerChatSession
        fields = ["id", "channel", "question_count", "first_question", "created_at", "last_activity"]

    def get_first_question(self, session):
        first = session.messages.filter(role=EmployerChatMessage.Role.USER).first()
        return first.content[:200] if first else ""
