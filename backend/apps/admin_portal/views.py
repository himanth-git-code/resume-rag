from datetime import datetime, time

from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.ai_profile.models import EmployerProfile
from apps.audit.models import AuditLog
from apps.candidates.services import CandidateProfileService
from apps.payments.models import Entitlement, Payment
from apps.support.models import SupportTicket
from apps.websites.catalog_admin import CatalogError, TemplateCatalogService
from apps.websites.models import TemplateCatalogVersion, Website

from .permissions import IsSuperuser
from .services import AdminActionError, AdminUserService, AIJobsService, OverviewService


class Pagination(PageNumberPagination):
    page_size = 25


def _paginate(request, qs, serialize):
    paginator = Pagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response([serialize(x) for x in page])


def _date(value, end=False):
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return timezone.make_aware(datetime.combine(d, time.max if end else time.min))


def _user_row(u):
    profile = getattr(u, "candidate_profile", None)
    website = getattr(u, "website", None)
    employer = getattr(u, "employer_profile", None)
    return {
        "id": u.pk,
        "email": u.email,
        "name": profile.full_name if profile else "",
        "date_joined": u.date_joined,
        "last_login": u.last_login,
        "is_active": u.is_active,
        "has_profile": getattr(u, "has_profile", profile is not None),
        "is_pro": getattr(u, "is_pro", False),
        "website": "blocked" if website and website.admin_blocked else "published" if website and website.published_version_id else "none",
        "ai_profile": "admin_disabled" if employer and employer.admin_disabled else "enabled" if employer and employer.enabled else "off",
    }


def _payment_row(p):
    return {
        "id": p.public_id, "user_id": p.user_id, "user_email": p.user.email, "product": p.product.name,
        "amount": p.amount, "currency": p.currency, "provider": p.provider, "status": p.status,
        "refunded_amount": p.refunded_amount,
        "refund_status": "full" if p.status == Payment.Status.REFUNDED else "partial" if p.refunded_amount else "none",
        "provider_order_id": p.provider_order_id, "provider_payment_id": p.provider_payment_id,
        "created_at": p.created_at, "paid_at": p.paid_at,
    }


def _audit_row(e):
    return {
        "id": e.pk, "action": e.action, "actor_type": e.actor_type,
        "actor_email": e.actor.email if e.actor else None,
        "subject_user_id": e.subject_user_id, "subject_email": e.subject_user.email if e.subject_user else None,
        "target_type": e.target_type, "target_id": e.target_id, "metadata": e.metadata, "created_at": e.created_at,
    }


@api_view(["GET"])
@permission_classes([IsSuperuser])
def overview(request):
    return Response(OverviewService.stats())


@api_view(["GET"])
@permission_classes([IsSuperuser])
def users(request):
    p = request.query_params
    qs = AdminUserService.search(
        q=(p.get("search") or "").strip()[:100] or None, profile=p.get("profile"), pro=p.get("pro"),
        website=p.get("website"), ai_profile=p.get("ai_profile"), account=p.get("account"),
    )
    return _paginate(request, qs, _user_row)


@api_view(["GET"])
@permission_classes([IsSuperuser])
def user_detail(request, user_id):
    try:
        user = AdminUserService.get(user_id)
    except AdminActionError:
        raise Http404 from None
    return Response(_user_detail_body(user))


def _user_detail_body(user) -> dict:
    website = Website.objects.filter(user=user).select_related("published_version").first()
    employer = EmployerProfile.objects.filter(user=user).first()
    return {
        **_user_row(user),
        "is_pro": Entitlement.objects.filter(user=user, code="website_publish", revoked_at__isnull=True).exists(),
        "profile": CandidateProfileService.get(user),
        "entitlements": [
            {"code": e.code, "source": e.source, "reason": e.reason, "granted_at": e.granted_at, "revoked_at": e.revoked_at,
             "granted_by": e.granted_by.email if e.granted_by else None}
            for e in Entitlement.objects.filter(user=user).select_related("granted_by").order_by("-granted_at")
        ],
        "payments": [_payment_row(x) for x in Payment.objects.filter(user=user).select_related("product", "user")[:20]],
        "website_detail": {
            "slug": website.slug if website else None,
            "template": website.template if website else None,
            "published_version": website.published_version.number if website and website.published_version else None,
            "admin_blocked": bool(website and website.admin_blocked),
            "admin_blocked_reason": website.admin_blocked_reason if website else "",
        },
        "ai_profile_detail": {
            "enabled": bool(employer and employer.enabled),
            "admin_disabled": bool(employer and employer.admin_disabled),
            "admin_disabled_reason": employer.admin_disabled_reason if employer else "",
            "chatbot_enabled": employer.chatbot_enabled if employer else True,
            "matching_enabled": employer.matching_enabled if employer else True,
        },
        "support": {
            "total": SupportTicket.objects.filter(candidate=user).count(),
            "open": SupportTicket.objects.filter(candidate=user).exclude(status__in=["resolved", "closed"]).count(),
        },
        "audit": [_audit_row(e) for e in AuditLog.objects.filter(subject_user=user).select_related("actor", "subject_user")[:30]],
    }


class ActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=sorted(AdminUserService.ACTIONS))
    reason = serializers.CharField(max_length=300, trim_whitespace=True)


@api_view(["POST"])
@permission_classes([IsSuperuser])
def user_action(request, user_id):
    serializer = ActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = AdminUserService.get(user_id)
        AdminUserService.act(request.user, user, serializer.validated_data["action"], serializer.validated_data["reason"], request)
    except AdminActionError as exc:
        if exc.status == 404:
            raise Http404 from None
        return Response({"detail": exc.message}, status=exc.status)
    user.refresh_from_db()
    return Response(_user_detail_body(user))


@api_view(["GET"])
@permission_classes([IsSuperuser])
def payments(request):
    p = request.query_params
    qs = Payment.objects.select_related("user", "product")
    if p.get("status"):
        qs = qs.filter(status=p["status"])
    if p.get("provider"):
        qs = qs.filter(provider=p["provider"])
    if start := _date(p.get("from")):
        qs = qs.filter(created_at__gte=start)
    if end := _date(p.get("to"), end=True):
        qs = qs.filter(created_at__lte=end)
    if search := (p.get("search") or "").strip()[:100]:
        qs = qs.filter(
            Q(user__email__icontains=search) | Q(public_id=search) | Q(provider_order_id=search) | Q(provider_payment_id=search)
        )
    return _paginate(request, qs, _payment_row)


@api_view(["GET"])
@permission_classes([IsSuperuser])
def ai_jobs(request):
    return Response(AIJobsService.summary())


@api_view(["GET"])
@permission_classes([IsSuperuser])
def audit(request):
    p = request.query_params
    qs = AuditLog.objects.select_related("actor", "subject_user")
    if action := (p.get("action") or "").strip():
        qs = qs.filter(action__startswith=action)
    if email := (p.get("user") or "").strip():
        qs = qs.filter(Q(subject_user__email__icontains=email) | Q(actor__email__icontains=email))
    if p.get("actor_type"):
        qs = qs.filter(actor_type=p["actor_type"])
    if start := _date(p.get("from")):
        qs = qs.filter(created_at__gte=start)
    if end := _date(p.get("to"), end=True):
        qs = qs.filter(created_at__lte=end)
    return _paginate(request, qs, _audit_row)


class TemplateUpdateSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=20)
    enabled = serializers.BooleanField(required=False)
    premium = serializers.BooleanField(required=False)
    name = serializers.CharField(max_length=60, required=False)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    default_sections = serializers.ListField(child=serializers.CharField(max_length=30), required=False, max_length=20)


@api_view(["GET", "PATCH"])
@permission_classes([IsSuperuser])
def templates(request):
    if request.method == "PATCH":
        serializer = TemplateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        try:
            TemplateCatalogService.update(request.user, data.pop("key"), data, request)
        except CatalogError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(TemplateCatalogService.list())


@api_view(["GET"])
@permission_classes([IsSuperuser])
def template_versions(request):
    return _paginate(
        request,
        TemplateCatalogVersion.objects.select_related("changed_by"),
        lambda v: {"number": v.number, "note": v.note, "changed_by": v.changed_by.email if v.changed_by else None,
                   "created_at": v.created_at},
    )


@api_view(["POST"])
@permission_classes([IsSuperuser])
def template_restore(request, number):
    try:
        TemplateCatalogService.restore(request.user, number, request)
    except CatalogError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(TemplateCatalogService.list())
