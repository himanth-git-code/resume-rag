from rest_framework import serializers

from .models import ResumeParseJob


class ResumeParseJobSerializer(serializers.ModelSerializer):
    document = serializers.SerializerMethodField()

    class Meta:
        model = ResumeParseJob
        fields = ["id", "status", "error_code", "error_message", "created_at", "completed_at", "document"]
        read_only_fields = fields

    def get_document(self, job):
        doc = job.document
        return {
            "id": doc.pk,
            "original_filename": doc.original_filename,
            "content_type": doc.content_type,
            "size": doc.size,
        }


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
