from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.documents.extraction import DocumentRejected

from .models import ResumeParseJob
from .serializers import ResumeParseJobSerializer, ResumeUploadSerializer
from .services import ResumeProcessingService


class UploadThrottle(UserRateThrottle):
    scope = "resume_upload"


def _get_job(request, job_id):
    try:
        return ResumeProcessingService.get_job_for(request.user, job_id)
    except ResumeParseJob.DoesNotExist:
        raise Http404 from None


@api_view(["POST"])
@parser_classes([MultiPartParser])
@throttle_classes([UploadThrottle])
def upload_resume(request):
    serializer = ResumeUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        job = ResumeProcessingService.create_job(request.user, serializer.validated_data["file"])
    except DocumentRejected as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ResumeParseJobSerializer(job).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def job_detail(request, job_id):
    return Response(ResumeParseJobSerializer(_get_job(request, job_id)).data)


@api_view(["GET"])
def latest_job(request):
    job = ResumeProcessingService.latest_job_for(request.user)
    if job is None:
        raise Http404
    return Response(ResumeParseJobSerializer(job).data)


@api_view(["POST"])
def retry_job(request, job_id):
    job = _get_job(request, job_id)
    if job.status != ResumeParseJob.Status.FAILED:
        return Response({"detail": "Only failed jobs can be retried."}, status=status.HTTP_409_CONFLICT)
    job = ResumeProcessingService.retry(job)
    return Response(ResumeParseJobSerializer(job).data)
