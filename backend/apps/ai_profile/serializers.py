from django.utils import timezone
from rest_framework import serializers

from .models import SECTIONS, EmployerProfile, ProfileAccessEvent


class EmployerProfileSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()
    visible_sections = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = [
            "enabled", "path", "token_created_at", "expires_at",
            "visible_sections", "chatbot_enabled", "matching_enabled",
        ]

    def get_path(self, profile):
        return f"/p/{profile.token}"

    def get_visible_sections(self, profile):
        return {section: profile.is_visible(section) for section in SECTIONS}


class EmployerProfileUpdateSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(required=False)
    chatbot_enabled = serializers.BooleanField(required=False)
    matching_enabled = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    visible_sections = serializers.DictField(child=serializers.BooleanField(), required=False)

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Choose a date in the future.")
        return value

    def validate_visible_sections(self, value):
        unknown = set(value) - set(SECTIONS)
        if unknown:
            raise serializers.ValidationError(f"Unknown sections: {', '.join(sorted(unknown))}")
        return value


class AccessEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAccessEvent
        fields = ["id", "kind", "created_at"]
