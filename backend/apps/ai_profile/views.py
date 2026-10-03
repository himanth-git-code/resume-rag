from django.conf import settings
from django.http import Http404
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.candidates.models import CandidateProfile

from .models import ProfileAccessEvent
from .public import PublicViewThrottle
from .serializers import AccessEventSerializer, EmployerProfileSerializer, EmployerProfileUpdateSerializer
from .services import EmployerProfileService, NotAvailable


def public_endpoint(*throttles):
    """Unauthenticated endpoint: no session (so no CSRF), throttled per client IP."""

    def decorate(view):
        view = throttle_classes(list(throttles))(view)
        view = permission_classes([AllowAny])(view)
        return authentication_classes([])(view)

    return decorate


def resolve_or_404(token):
    try:
        return EmployerProfileService.resolve(token)
    except NotAvailable:
        raise Http404 from None


@api_view(["GET", "PUT"])
def employer_profile(request):
    profile = EmployerProfileService.get_or_create(request.user)
    if request.method == "PUT":
        serializer = EmployerProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = EmployerProfileService.update(profile, serializer.validated_data, request)
    body = EmployerProfileSerializer(profile).data
    body["has_profile"] = CandidateProfile.objects.filter(user=request.user).exists()
    return Response(body)


@api_view(["POST"])
def regenerate_link(request):
    profile = EmployerProfileService.regenerate_link(EmployerProfileService.get_or_create(request.user))
    return Response(EmployerProfileSerializer(profile).data)


class ActivityPagination(PageNumberPagination):
    page_size = 25


@api_view(["GET"])
def activity(request):
    profile = EmployerProfileService.get_or_create(request.user)
    summary = EmployerProfileService.activity(profile)
    paginator = ActivityPagination()
    page = paginator.paginate_queryset(summary["events"], request)
    response = paginator.get_paginated_response(AccessEventSerializer(page, many=True).data)
    response.data["views"] = summary["views"]
    response.data["unique_visitors"] = summary["unique_visitors"]
    return response


@api_view(["GET"])
@public_endpoint(PublicViewThrottle)
def public_profile(request, token):
    profile = resolve_or_404(token)
    EmployerProfileService.log_event(profile, ProfileAccessEvent.Kind.VIEW, request)
    return Response(
        {
            "profile": EmployerProfileService.public_view(profile),
            "chatbot_enabled": profile.chatbot_enabled,
            "matching_enabled": profile.matching_enabled,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY or None,
        }
    )
