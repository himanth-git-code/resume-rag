from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.ai_profile.public import PublicChatThrottle, PublicPollThrottle
from apps.ai_profile.services import EmployerProfileService
from apps.ai_profile.views import public_endpoint, resolve_or_404

from .models import EmployerChatSession
from .serializers import AskSerializer, MessageSerializer, SessionSummarySerializer
from .services import ChatError, EmployerChatService


def _chat_profile(token):
    profile = resolve_or_404(token)
    if not profile.chatbot_enabled:
        raise Http404
    return profile


@api_view(["POST"])
@public_endpoint(PublicChatThrottle)
def ask(request, token):
    profile = _chat_profile(token)
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
        )
    except ChatError as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=exc.status)
    return Response(
        {"session_id": session.public_id, "messages": MessageSerializer(messages, many=True).data},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@public_endpoint(PublicPollThrottle)
def transcript(request, token, session_id):
    profile = _chat_profile(token)
    session = EmployerChatSession.objects.filter(profile=profile, public_id=session_id).first()
    if session is None:
        raise Http404
    return Response(
        {"session_id": session.public_id, "messages": MessageSerializer(EmployerChatService.transcript(session), many=True).data}
    )


class SessionPagination(PageNumberPagination):
    page_size = 20


@api_view(["GET"])
def my_sessions(request):
    """The candidate's own view of employer conversations (SPEC §9 activity history)."""
    profile = EmployerProfileService.get_or_create(request.user)
    paginator = SessionPagination()
    page = paginator.paginate_queryset(profile.chat_sessions.all(), request)
    return paginator.get_paginated_response(SessionSummarySerializer(page, many=True).data)


@api_view(["GET"])
def my_session_detail(request, session_id):
    session = EmployerChatSession.objects.filter(profile__user=request.user, public_id=session_id).first()
    if session is None:
        raise Http404
    return Response(
        {
            **SessionSummarySerializer(session).data,
            "messages": MessageSerializer(EmployerChatService.transcript(session), many=True).data,
        }
    )
