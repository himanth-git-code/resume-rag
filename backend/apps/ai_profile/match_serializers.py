from rest_framework import serializers

from .matching import DISCLAIMER
from .models import JobMatchRequest


class JobMatchSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id")
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = JobMatchRequest
        fields = [
            "id", "source", "status", "job_title", "score", "requirements", "summary",
            "error_message", "disclaimer", "created_at", "completed_at",
        ]

    def get_disclaimer(self, match):
        return DISCLAIMER


class JobMatchSummarySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id")

    class Meta:
        model = JobMatchRequest
        fields = ["id", "source", "status", "job_title", "score", "created_at"]


class MatchInputSerializer(serializers.Serializer):
    # Length limits are enforced (with friendly messages) by JobMatchService.
    job_description = serializers.CharField(max_length=20_000, trim_whitespace=True)
    turnstile_token = serializers.CharField(max_length=4096, required=False, allow_null=True, allow_blank=True)
