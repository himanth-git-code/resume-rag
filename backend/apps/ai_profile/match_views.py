from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .match_serializers import JobMatchSerializer, JobMatchSummarySerializer, MatchInputSerializer
from .matching import JobMatchService, MatchError
from .models import JobMatchRequest
from .public import PublicMatchThrottle, PublicPollThrottle, verify_turnstile
from .services import EmployerProfileService
from .views import public_endpoint, resolve_or_404


class SelfMatchThrottle(UserRateThrottle):
    scope = "public_match"


def _matching_profile(token):
    profile = resolve_or_404(token)
    if not profile.matching_enabled:
        raise Http404
    return profile


def _start(profile, request, source):
    serializer = MatchInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        match = JobMatchService.request(
            profile, serializer.validated_data["job_description"], source=source, request=request
        )
    except MatchError as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=exc.status)
    return Response(JobMatchSerializer(match).data, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@public_endpoint(PublicMatchThrottle)
def public_match(request, token):
    profile = _matching_profile(token)
    if not verify_turnstile(request.data.get("turnstile_token"), request):
        return Response(
            {"code": "bot_check", "detail": "Please complete the verification and try again."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return _start(profile, request, JobMatchRequest.Source.EMPLOYER_PROFILE)


@api_view(["GET"])
@public_endpoint(PublicPollThrottle)
def public_match_detail(request, token, match_id):
    profile = _matching_profile(token)
    match = profile.matches.filter(public_id=match_id, source=JobMatchRequest.Source.EMPLOYER_PROFILE).first()
    if match is None:
        raise Http404
    return Response(JobMatchSerializer(match).data)


class MatchPagination(PageNumberPagination):
    page_size = 20


@api_view(["GET", "POST"])
@throttle_classes([SelfMatchThrottle])
def my_matches(request):
    profile = EmployerProfileService.get_or_create(request.user)
    if request.method == "POST":
        return _start(profile, request, JobMatchRequest.Source.CANDIDATE_SELF)
    paginator = MatchPagination()
    page = paginator.paginate_queryset(profile.matches.all(), request)
    return paginator.get_paginated_response(JobMatchSummarySerializer(page, many=True).data)


@api_view(["GET"])
def my_match_detail(request, match_id):
    match = JobMatchRequest.objects.filter(profile__user=request.user, public_id=match_id).first()
    if match is None:
        raise Http404
    return Response(JobMatchSerializer(match).data)
