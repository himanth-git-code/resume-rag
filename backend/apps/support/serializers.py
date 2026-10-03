from rest_framework import serializers

from .models import SupportAttachment, SupportMessage, SupportTicket


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = SupportAttachment
        fields = ["id", "original_name", "content_type", "size", "url"]

    def get_url(self, attachment):
        return f"/api/support/attachments/{attachment.pk}/"


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SupportMessage
        fields = ["id", "kind", "author", "body", "attachments", "created_at"]

    def get_author(self, message):
        if message.author is None:
            return None
        if message.kind == SupportMessage.Kind.CANDIDATE:
            return {"name": "You" if self.context.get("candidate_view") else message.author.email, "staff": False}
        return {"name": message.author.get_full_name() or "Support team", "staff": True}


def _user_label(user):
    return {"id": user.pk, "email": user.email, "name": user.get_full_name() or user.email} if user else None


class TicketSummarySerializer(serializers.ModelSerializer):
    unread = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = SupportTicket
        fields = ["number", "subject", "priority", "status", "unread", "created_at", "updated_at"]


class StaffTicketSummarySerializer(TicketSummarySerializer):
    candidate = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta(TicketSummarySerializer.Meta):
        fields = TicketSummarySerializer.Meta.fields + ["candidate", "assigned_to"]

    def get_candidate(self, ticket):
        return _user_label(ticket.candidate)

    def get_assigned_to(self, ticket):
        return _user_label(ticket.assigned_to)


class CreateTicketSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200, trim_whitespace=True)
    description = serializers.CharField(max_length=5000, trim_whitespace=True)
    priority = serializers.ChoiceField(choices=["low", "normal", "high"], default="normal")


class ReplySerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000, trim_whitespace=True)


class StaffReplySerializer(ReplySerializer):
    internal = serializers.BooleanField(default=False)
    status = serializers.ChoiceField(choices=SupportTicket.Status.choices, required=False, allow_null=True)


class StaffUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SupportTicket.Status.choices, required=False)
    priority = serializers.ChoiceField(choices=SupportTicket.Priority.choices, required=False)
    assigned_to = serializers.IntegerField(required=False, allow_null=True)
