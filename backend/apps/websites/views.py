from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.ai_profile.public import PublicPollThrottle
from apps.ai_profile.views import public_endpoint
from apps.candidates.models import CandidateProfile

from .bio import BioService
from .catalog import catalog as catalog_data
from .serializers import BioDraftRequestSerializer, WebsiteSerializer, WebsiteUpdateSerializer
from .services import PublishError, PublishingService, SlugError, WebsiteService


class PreviewThrottle(UserRateThrottle):
    scope = "website_preview"


class BioDraftThrottle(UserRateThrottle):
    scope = "question_generate"


def _payload(website):
    body = WebsiteSerializer(website).data
    body["has_profile"] = CandidateProfile.objects.filter(user=website.user).exists()
    body["suggested_slug"] = None if website.slug else WebsiteService.suggest_slug(website)
    body["publish_problems"] = WebsiteService.publish_problems(website)
    body["publish"] = PublishingService.status(website)
    return body


@api_view(["GET", "PUT"])
def website(request):
    site = WebsiteService.get_or_create(request.user)
    if request.method == "PUT":
        serializer = WebsiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            site = WebsiteService.update(site, serializer.validated_data)
        except SlugError as exc:
            return Response({"slug": [exc.message]}, status=status.HTTP_400_BAD_REQUEST)
    return Response(_payload(site))


@api_view(["GET"])
def slug_available(request):
    site = WebsiteService.get_or_create(request.user)
    try:
        WebsiteService.validate_slug(request.query_params.get("slug", ""), site)
    except SlugError as exc:
        return Response({"available": False, "detail": exc.message})
    return Response({"available": True, "detail": None})


@api_view(["GET"])
def catalog(request):
    return Response(catalog_data())


@api_view(["POST"])
@throttle_classes([BioDraftThrottle])
def draft_bio(request):
    serializer = BioDraftRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    site = WebsiteService.get_or_create(request.user)
    if not CandidateProfile.objects.filter(user=request.user).exists():
        return Response({"detail": "Save your profile first."}, status=status.HTTP_409_CONFLICT)
    site = BioService.request_draft(site, serializer.validated_data["person"])
    return Response(_payload(site), status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@throttle_classes([PreviewThrottle])
def preview(request):
    site = WebsiteService.get_or_create(request.user)
    token = WebsiteService.issue_preview(site)
    return Response({"path": f"/portfolio-preview/{token.token}", "expires_at": token.expires_at}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@public_endpoint(PublicPollThrottle)
def render_preview(request, token):
    """Called server-side by the Next.js preview page. The token is the only credential."""
    site = WebsiteService.resolve_preview(token, request)
    if site is None:
        return Response({"detail": "This preview link has expired."}, status=status.HTTP_404_NOT_FOUND)
    return Response(WebsiteService.build_site_data(site))


@api_view(["POST"])
def publish(request):
    site = WebsiteService.get_or_create(request.user)
    try:
        PublishingService.publish(site, request)
    except PublishError as exc:
        return Response({"detail": " ".join(exc.problems), "problems": exc.problems}, status=status.HTTP_409_CONFLICT)
    site.refresh_from_db()
    return Response(_payload(site))


@api_view(["POST"])
def unpublish(request):
    site = WebsiteService.get_or_create(request.user)
    PublishingService.unpublish(site, request)
    site.refresh_from_db()
    return Response(_payload(site))
