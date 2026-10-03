"""Admin dashboard queries and actions (SPEC §16). Every action is audited."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.ai_profile.models import EmployerProfile, JobMatchRequest
from apps.audit.services import record
from apps.candidates.models import CandidateProfile
from apps.chatbot.models import EmployerChatMessage
from apps.knowledge_base.models import KnowledgeBaseState
from apps.payments.models import Entitlement, Payment, Product
from apps.payments.services import EntitlementService
from apps.questions.models import QuestionGeneration
from apps.resume_parser.models import ResumeParseJob
from apps.support.models import SupportTicket
from apps.websites.models import Website
from apps.websites.services import PublishingService

User = get_user_model()
ACTIVE_WINDOW = timedelta(days=30)
STUCK_AFTER = timedelta(minutes=30)
PRO_CODE = "pro"


class AdminActionError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def candidates():
    return User.objects.filter(is_staff=False, is_superuser=False)


class OverviewService:
    @staticmethod
    def stats() -> dict:
        now = timezone.now()
        since = now - ACTIVE_WINDOW
        users = candidates()
        successful = Payment.objects.filter(status__in=[Payment.Status.SUCCESSFUL, Payment.Status.REFUNDED])
        revenue = [
            {"currency": row["currency"], "amount": (row["gross"] or 0) - (row["refunded"] or 0)}
            for row in successful.values("currency").annotate(gross=Sum("amount"), refunded=Sum("refunded_amount"))
        ]
        recent_revenue = [
            {"currency": row["currency"], "amount": (row["gross"] or 0) - (row["refunded"] or 0)}
            for row in successful.filter(paid_at__gte=since)
            .values("currency")
            .annotate(gross=Sum("amount"), refunded=Sum("refunded_amount"))
        ]
        return {
            "registrations": users.count(),
            "registrations_30d": users.filter(date_joined__gte=since).count(),
            "active_candidates": users.filter(is_active=True, last_login__gte=since).count(),
            "suspended": users.filter(is_active=False).count(),
            "completed_profiles": CandidateProfile.objects.filter(user__in=users).count(),
            "published_websites": Website.objects.filter(published_version__isnull=False, admin_blocked=False).count(),
            "enabled_employer_profiles": EmployerProfile.objects.filter(enabled=True, admin_disabled=False).count(),
            "payments_total": Payment.objects.exclude(status=Payment.Status.PENDING).count(),
            "payments_successful": successful.count(),
            "revenue": revenue,
            "revenue_30d": recent_revenue,
            "open_support_tickets": SupportTicket.objects.exclude(
                status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
            ).count(),
            "signups_by_day": [
                {"date": row["day"].isoformat(), "count": row["n"]}
                for row in users.filter(date_joined__gte=since)
                .annotate(day=TruncDate("date_joined"))
                .values("day")
                .annotate(n=Count("id"))
                .order_by("day")
            ],
        }


class AdminUserService:
    @staticmethod
    def search(*, q=None, profile=None, pro=None, website=None, ai_profile=None, account=None):
        qs = candidates().select_related("candidate_profile", "website", "employer_profile").annotate(
            has_profile=Exists(CandidateProfile.objects.filter(user=OuterRef("pk"))),
            is_pro=Exists(Entitlement.objects.filter(user=OuterRef("pk"), code="website_publish", revoked_at__isnull=True)),
        )
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(candidate_profile__full_name__icontains=q))
        if profile in ("yes", "no"):
            qs = qs.filter(has_profile=profile == "yes")
        if pro in ("yes", "no"):
            qs = qs.filter(is_pro=pro == "yes")
        if website == "published":
            qs = qs.filter(website__published_version__isnull=False, website__admin_blocked=False)
        elif website == "blocked":
            qs = qs.filter(website__admin_blocked=True)
        if ai_profile == "enabled":
            qs = qs.filter(employer_profile__enabled=True, employer_profile__admin_disabled=False)
        elif ai_profile == "admin_disabled":
            qs = qs.filter(employer_profile__admin_disabled=True)
        if account == "active":
            qs = qs.filter(is_active=True)
        elif account == "suspended":
            qs = qs.filter(is_active=False)
        return qs.order_by("-date_joined", "-pk")

    @staticmethod
    def get(user_id: int):
        user = candidates().filter(pk=user_id).first()
        if user is None:
            raise AdminActionError("Not found.", status=404)
        return user

    ACTIONS = {
        "suspend", "reactivate", "disable_ai_profile", "enable_ai_profile",
        "take_site_offline", "allow_publishing", "grant_pro", "revoke_pro",
    }

    @staticmethod
    @transaction.atomic
    def act(admin, user, action: str, reason: str, request=None) -> None:
        reason = (reason or "").strip()
        if action not in AdminUserService.ACTIONS:
            raise AdminActionError("Unknown action.")
        if not reason:
            raise AdminActionError("Give a reason; it's kept in the audit log.")
        if user.is_staff or user.is_superuser:
            raise AdminActionError("Staff accounts can't be changed here.", status=403)

        if action == "suspend":
            user.is_active = False
            user.save(update_fields=["is_active"])
        elif action == "reactivate":
            user.is_active = True
            user.save(update_fields=["is_active"])
        elif action in ("disable_ai_profile", "enable_ai_profile"):
            profile, _ = EmployerProfile.objects.get_or_create(user=user)
            profile.admin_disabled = action == "disable_ai_profile"
            profile.admin_disabled_reason = reason[:300] if profile.admin_disabled else ""
            profile.save(update_fields=["admin_disabled", "admin_disabled_reason", "updated_at"])
        elif action in ("take_site_offline", "allow_publishing"):
            website, _ = Website.objects.get_or_create(user=user)
            website.admin_blocked = action == "take_site_offline"
            website.admin_blocked_reason = reason[:300] if website.admin_blocked else ""
            website.save(update_fields=["admin_blocked", "admin_blocked_reason", "updated_at"])
            if website.admin_blocked:
                PublishingService.unpublish(website, request, actor=admin)
        elif action == "grant_pro":
            product = Product.objects.get(code=PRO_CODE)
            EntitlementService.grant(user, product.entitlements, None, granted_by=admin, reason=reason)
        elif action == "revoke_pro":
            product = Product.objects.get(code=PRO_CODE)
            if not EntitlementService.revoke_all(user, product.entitlements):
                raise AdminActionError("This user doesn't have Pro.")

        record(f"admin.{action}", actor=admin, request=request, subject_user=user, target=user, reason=reason[:300])


def _counts(qs, field="status") -> dict:
    return {row[field]: row["n"] for row in qs.values(field).annotate(n=Count("id"))}


class AIJobsService:
    @staticmethod
    def summary(days: int = 7) -> dict:
        now = timezone.now()
        since, stuck_before = now - timedelta(days=days), now - STUCK_AFTER

        parse = ResumeParseJob.objects.filter(created_at__gte=since)
        questions = QuestionGeneration.objects.filter(created_at__gte=since)
        chat = EmployerChatMessage.objects.filter(role="assistant", created_at__gte=since)
        matches = JobMatchRequest.objects.filter(created_at__gte=since)
        bios = Website.objects.filter(bio_draft_requested_at__gte=since).exclude(bio_draft_status="")

        def failures(qs, *, owner_path, error_field="error_code", time_field="created_at", limit=10):
            rows = qs.filter(status="failed").select_related().order_by(f"-{time_field}")[:limit]
            out = []
            for row in rows:
                owner = row
                for part in owner_path.split("__"):
                    owner = getattr(owner, part, None)
                out.append({
                    "id": row.pk, "user_id": getattr(owner, "pk", None), "user_email": getattr(owner, "email", None),
                    "error_code": getattr(row, error_field, "") or "", "at": getattr(row, time_field),
                })
            return out

        return {
            "window_days": days,
            "pipelines": [
                {"key": "resume_parsing", "label": "Resume parsing", "counts": _counts(parse),
                 "failures": failures(parse, owner_path="document__owner"),
                 "stuck": parse.filter(status__in=["pending", "parsing"], created_at__lt=stuck_before).count()},
                {"key": "questions", "label": "Question generation", "counts": _counts(questions),
                 "failures": failures(questions, owner_path="owner"),
                 "stuck": questions.filter(status__in=["pending", "running"], created_at__lt=stuck_before).count()},
                {"key": "knowledge_base", "label": "Knowledge base", "counts": _counts(KnowledgeBaseState.objects.all()),
                 "failures": [
                     {"id": s.pk, "user_id": s.owner_id, "user_email": s.owner.email, "error_code": s.error_code, "at": s.updated_at}
                     for s in KnowledgeBaseState.objects.filter(status="failed").select_related("owner").order_by("-updated_at")[:10]
                 ],
                 "stuck": KnowledgeBaseState.objects.filter(status="indexing", updated_at__lt=stuck_before).count()},
                {"key": "chat", "label": "Employer chat replies", "counts": _counts(chat),
                 "failures": failures(chat, owner_path="session__profile__user"),
                 "stuck": chat.filter(status="pending", created_at__lt=stuck_before).count()},
                {"key": "job_matching", "label": "Job matching", "counts": _counts(matches),
                 "failures": failures(matches, owner_path="profile__user"),
                 "stuck": matches.filter(status__in=["pending", "running"], created_at__lt=stuck_before).count()},
                {"key": "bio_drafts", "label": "Website bio drafts", "counts": _counts(bios, "bio_draft_status"),
                 "failures": [
                     {"id": w.pk, "user_id": w.user_id, "user_email": w.user.email, "error_code": "", "at": w.bio_draft_requested_at}
                     for w in bios.filter(bio_draft_status="failed").select_related("user").order_by("-bio_draft_requested_at")[:10]
                 ],
                 "stuck": bios.filter(bio_draft_status="pending", bio_draft_requested_at__lt=stuck_before).count()},
            ],
        }
