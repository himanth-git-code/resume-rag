from rest_framework import serializers

from .catalog import FONTS, MODES, PALETTES, SECTIONS, TEMPLATES
from .models import Website


class SectionSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=list(SECTIONS))
    visible = serializers.BooleanField()


class ThemeSerializer(serializers.Serializer):
    palette = serializers.ChoiceField(choices=list(PALETTES), required=False)
    mode = serializers.ChoiceField(choices=list(MODES), required=False)
    font = serializers.ChoiceField(choices=list(FONTS), required=False)


class OverridesSerializer(serializers.Serializer):
    tagline = serializers.CharField(max_length=160, required=False, allow_blank=True, trim_whitespace=True)
    intro = serializers.CharField(max_length=1000, required=False, allow_blank=True, trim_whitespace=True)
    titles = serializers.DictField(child=serializers.CharField(max_length=60, allow_blank=True), required=False)
    featured_projects = serializers.ListField(child=serializers.IntegerField(), required=False, allow_null=True, max_length=100)
    featured_achievements = serializers.ListField(child=serializers.IntegerField(), required=False, allow_null=True, max_length=100)
    leadership = serializers.ListField(child=serializers.CharField(max_length=1000), required=False, max_length=20)

    def validate_titles(self, value):
        unknown = set(value) - set(SECTIONS)
        if unknown:
            raise serializers.ValidationError(f"Unknown sections: {', '.join(sorted(unknown))}")
        return value


class WebsiteUpdateSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=60, required=False, allow_blank=True, allow_null=True)
    template = serializers.ChoiceField(choices=list(TEMPLATES), required=False)
    theme = ThemeSerializer(required=False)
    sections = SectionSerializer(many=True, required=False, max_length=len(SECTIONS))
    overrides = OverridesSerializer(required=False)
    bio_text = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    show_chatbot = serializers.BooleanField(required=False)
    show_matching = serializers.BooleanField(required=False)


class WebsiteSerializer(serializers.ModelSerializer):
    bio = serializers.SerializerMethodField()
    bio_draft = serializers.SerializerMethodField()

    class Meta:
        model = Website
        fields = ["slug", "template", "theme", "sections", "overrides", "bio", "bio_draft", "show_chatbot", "show_matching", "updated_at"]

    def get_bio(self, website):
        return {"text": website.bio_text, "source": website.bio_source or None, "approved_at": website.bio_approved_at}

    def get_bio_draft(self, website):
        return {"status": website.bio_draft_status or None, "text": website.bio_draft_text or None}


class BioDraftRequestSerializer(serializers.Serializer):
    person = serializers.ChoiceField(choices=["first", "third"], default="first")
