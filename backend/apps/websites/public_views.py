"""Public website endpoints: the published site and its embedded chat/match widgets.

Widgets reuse the employer chatbot and job matching services, limited to what the
published site shows, and only when both the site and the candidate's global
switches allow them (SPEC §11).
"""

from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.ai_profile.match_serializers import JobMatchSerializer
from apps.ai_profile.match_views import MatchInputSerializer
from apps.ai_profile.matching import JobMatchService, MatchError
from apps.ai_profile.models import JobMatchRequest
from apps.ai_profile.public import (
    PublicChatThrottle,
    PublicMatchThrottle,
    PublicPollThrottle,
    PublicViewThrottle,
    verify_turnstile,
)
from apps.ai_profile.services import EmployerProfileService
from apps.ai_profile.views import public_endpoint
from apps.chatbot.models import Channel, EmployerChatSession
from apps.chatbot.serializers import AskSerializer, MessageSerializer
from apps.chatbot.services import ChatError, EmployerChatService

from .services import PublishingService


def _site_or_404(slug):
    site = PublishingService.resolve_public(slug)
    if site is None:
        raise Http404
    return site


def _widget_site(slug, widget):
    site = _site_or_404(slug)
    if not PublishingService.widget_flags(site)[widget]:
        raise Http404
    return site, EmployerProfileService.get_or_create(site.user)


@api_view(["GET"])
@public_endpoint(PublicViewThrottle)
def public_site(request, slug):
    return Response(PublishingService.public_data(_site_or_404(slug), request))


@api_view(["POST"])
@public_endpoint(PublicChatThrottle)
def site_chat(request, slug):
    site, profile = _widget_site(slug, "chatbot")
    serializer = AskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        session, messages = EmployerChatService.ask(
            profile,
            question=data["message"],
            session_id=data.get("session_id") or None,
            request=request,
            turnstile_token=data.get("turnstile_token"),
            channel=Channel.WEBSITE,
            source_types=PublishingService.source_types(site),
        )
    except ChatError as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=exc.status)
    return Response(
        {"session_id": session.public_id, "messages": MessageSerializer(messages, many=True).data},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@public_endpoint(PublicPollThrottle)
def site_chat_transcript(request, slug, session_id):
    site, profile = _widget_site(slug, "chatbot")
    session = EmployerChatSession.objects.filter(profile=profile, public_id=session_id, channel=Channel.WEBSITE).first()
    if session is None:
        raise Http404
    return Response(
        {"session_id": session.public_id, "messages": MessageSerializer(EmployerChatService.transcript(session), many=True).data}
    )


@api_view(["POST"])
@public_endpoint(PublicMatchThrottle)
def site_match(request, slug):
    site, profile = _widget_site(slug, "matching")
    if not verify_turnstile(request.data.get("turnstile_token"), request):
        return Response(
            {"code": "bot_check", "detail": "Please complete the verification and try again."},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = MatchInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        match = JobMatchService.request(
            profile,
            serializer.validated_data["job_description"],
            source=JobMatchRequest.Source.WEBSITE,
            request=request,
            source_types=PublishingService.source_types(site),
        )
    except MatchError as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=exc.status)
    return Response(JobMatchSerializer(match).data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@public_endpoint(PublicPollThrottle)
def site_match_detail(request, slug, match_id):
    site, profile = _widget_site(slug, "matching")
    match = profile.matches.filter(public_id=match_id, source=JobMatchRequest.Source.WEBSITE).first()
    if match is None:
        raise Http404
    return Response(JobMatchSerializer(match).data)
