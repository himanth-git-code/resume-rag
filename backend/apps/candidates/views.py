from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.knowledge_base.services import KnowledgeBaseService
from apps.payments.services import EntitlementService
from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.services import ResumeProcessingService

from .models import CandidateNote
from .serializers import NoteSerializer, SaveProfileSerializer
from .services import CandidateDashboardService, CandidateNoteService, CandidateProfileService, DraftNotAvailable


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
            "knowledge_base": KnowledgeBaseService.state_for(user),
            "entitlements": sorted(EntitlementService.active_codes(user)),
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


@api_view(["GET", "POST"])
def notes(request):
    if request.method == "GET":
        return Response(NoteSerializer(CandidateNoteService.list(request.user), many=True).data)
    serializer = NoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    note = CandidateNoteService.create(request.user, **serializer.validated_data)
    return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
def note_detail(request, note_id):
    try:
        note = CandidateNoteService.get(request.user, note_id)
    except CandidateNote.DoesNotExist:
        raise Http404 from None

    if request.method == "GET":
        return Response(NoteSerializer(note).data)
    if request.method == "DELETE":
        CandidateNoteService.delete(note)
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = NoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(NoteSerializer(CandidateNoteService.update(note, **serializer.validated_data)).data)
