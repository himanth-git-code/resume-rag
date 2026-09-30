from rest_framework import serializers

from .models import Question, QuestionGeneration


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "text", "difficulty", "talking_points"]


class QuestionSerializer(serializers.ModelSerializer):
    follow_ups = FollowUpSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "category", "difficulty", "topic", "text", "source_refs", "talking_points", "follow_ups"]


class GenerationSerializer(serializers.ModelSerializer):
    sections_total = serializers.SerializerMethodField()
    sections_done = serializers.SerializerMethodField()

    class Meta:
        model = QuestionGeneration
        fields = [
            "id", "kind", "scope", "status", "sections_total", "sections_done",
            "error_code", "error_message", "created_at", "completed_at",
        ]

    def get_sections_total(self, gen):
        return len(gen.sections)

    def get_sections_done(self, gen):
        return len(gen.completed_sections)


class GenerateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=QuestionGeneration.Kind.choices)
    category = serializers.ChoiceField(choices=Question.Category.choices, required=False, allow_null=True)
    source = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
