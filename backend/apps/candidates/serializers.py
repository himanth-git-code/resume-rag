"""Validation for the profile payload (same shape as ResumeExtraction).

Missing text is `null` on the wire and stored as "" in the database.
"""

import re

from rest_framework import serializers

from .models import SourceType

MAX_ITEMS = 100
MAX_LIST_ENTRIES = 50

_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")
_HOST_PORT = re.compile(r"^[\w.-]+:\d")


def validate_link(value: str | None) -> str | None:
    """Allow http(s) and scheme-less URLs ("linkedin.com/in/jane"); reject javascript:, data:, etc.

    These links are shown to employers later, so unsafe schemes must never be stored.
    """
    if not value:
        return value
    value = value.strip()
    match = _SCHEME.match(value)
    # "host:port/path" looks like a scheme but isn't one.
    if match and not _HOST_PORT.match(value) and match.group(1).lower() not in ("http", "https"):
        raise serializers.ValidationError("Enter a web address starting with http:// or https://.")
    return value


def text(max_length, required=False):
    return serializers.CharField(
        max_length=max_length, required=required, allow_blank=not required, allow_null=not required, trim_whitespace=True
    )


def string_list(max_length=1000):
    return serializers.ListField(
        child=serializers.CharField(max_length=max_length, trim_whitespace=True),
        max_length=MAX_LIST_ENTRIES,
        required=False,
        default=list,
    )


class ItemSerializer(serializers.Serializer):
    # Existing row to update. Only honoured if it belongs to this profile.
    id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    source_type = serializers.ChoiceField(choices=SourceType.choices, required=False, default=SourceType.CANDIDATE_INPUT)


class LinkSerializer(ItemSerializer):
    label = text(100)
    url = serializers.CharField(max_length=500, validators=[validate_link])


class SkillSerializer(ItemSerializer):
    name = text(100, required=True)
    category = text(100)


class ExperienceSerializer(ItemSerializer):
    company = text(200)
    title = text(200)
    location = text(200)
    start_date = text(50)
    end_date = text(50)
    is_current = serializers.BooleanField(required=False, allow_null=True, default=None)
    description = text(5000)
    responsibilities = string_list()
    achievements = string_list()
    technologies = string_list(100)

    def validate(self, attrs):
        if not (attrs.get("company") or attrs.get("title")):
            raise serializers.ValidationError("Add at least a company or a job title.")
        return attrs


class EducationSerializer(ItemSerializer):
    institution = text(200)
    degree = text(200)
    field_of_study = text(200)
    start_date = text(50)
    end_date = text(50)
    grade = text(100)

    def validate(self, attrs):
        if not (attrs.get("institution") or attrs.get("degree")):
            raise serializers.ValidationError("Add at least an institution or a degree.")
        return attrs


class CertificationSerializer(ItemSerializer):
    name = text(200, required=True)
    issuer = text(200)
    issue_date = text(50)
    expiry_date = text(50)
    credential_id = text(200)
    url = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True, validators=[validate_link])


class ProjectSerializer(ItemSerializer):
    name = text(200, required=True)
    role = text(200)
    description = text(5000)
    technologies = string_list(100)
    url = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True, validators=[validate_link])
    start_date = text(50)
    end_date = text(50)


class AchievementSerializer(ItemSerializer):
    title = text(300, required=True)
    description = text(5000)
    date = text(50)


def section(serializer_class):
    return serializer_class(many=True, required=False, default=list, max_length=MAX_ITEMS)


class ProfileSerializer(serializers.Serializer):
    full_name = text(200)
    headline = text(200)
    summary = text(10000)
    email = text(254)
    phone = text(50)
    location = text(200)
    links = section(LinkSerializer)
    skills = section(SkillSerializer)
    experience = section(ExperienceSerializer)
    education = section(EducationSerializer)
    certifications = section(CertificationSerializer)
    projects = section(ProjectSerializer)
    achievements = section(AchievementSerializer)


class SaveProfileSerializer(ProfileSerializer):
    # The parse job whose draft was reviewed, if any. Ownership is checked in the view.
    job_id = serializers.IntegerField(required=False, allow_null=True)


class NoteSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    body = serializers.CharField(max_length=10000, trim_whitespace=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
