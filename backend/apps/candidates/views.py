from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.services import ResumeProcessingService

from .serializers import SaveProfileSerializer
from .services import CandidateDashboardService, CandidateProfileService, DraftNotAvailable


def _get_job(request, job_id):
    try:
        return ResumeProcessingService.get_job_for(request.user, job_id)
    except ResumeParseJob.DoesNotExist:
        raise Http404 from None


@api_view(["GET"])
def me(request):
    user = request.user
    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "dashboard": CandidateDashboardService.get_state(user),
        }
    )


@api_view(["GET", "PUT"])
def profile(request):
    if request.method == "GET":
        data = CandidateProfileService.get(request.user)
        if data is None:
            raise Http404
        return Response(data)

    serializer = SaveProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = dict(serializer.validated_data)
    job_id = payload.pop("job_id", None)
    job = _get_job(request, job_id) if job_id is not None else None
    try:
        data = CandidateProfileService.save(request.user, payload, job=job)
    except DraftNotAvailable:
        return Response({"detail": "This resume hasn't finished processing."}, status=status.HTTP_409_CONFLICT)
    return Response(data)


@api_view(["GET"])
def job_draft(request, job_id):
    job = _get_job(request, job_id)
    try:
        return Response(CandidateProfileService.draft_for(job))
    except DraftNotAvailable:
        return Response({"detail": "This resume hasn't finished processing."}, status=status.HTTP_409_CONFLICT)
