from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_profile.services import EmployerProfileService
from apps.audit.models import AuditLog
from apps.candidates.services import CandidateProfileService
from apps.payments.models import Payment, Product
from apps.payments.services import EntitlementService
from apps.resume_parser.models import ResumeParseJob
from apps.websites.models import Website


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def admin(make_user):
    user = make_user("boss@example.com")
    user.is_staff = user.is_superuser = True
    user.save()
    c = client_for(user)
    c.user = user
    return c


@pytest.fixture
def support_agent(make_user):
    user = make_user("agent@example.com")
    user.is_staff = True
    user.save()
    return client_for(user)


@pytest.fixture
def jane(user):
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        CandidateProfileService.save(user, {"full_name": "Jane Doe", "skills": [{"name": "Python"}]})
    return user


def act(admin, user, action, reason="Testing"):
    return admin.post(f"/api/admin/users/{user.pk}/actions/", {"action": action, "reason": reason}, format="json")


ADMIN_URLS = ["/api/admin/overview/", "/api/admin/users/", "/api/admin/payments/", "/api/admin/ai-jobs/",
              "/api/admin/audit/", "/api/admin/templates/"]


@pytest.mark.parametrize("url", ADMIN_URLS)
def test_only_superusers_reach_the_admin_api(url, api, support_agent, admin):
    assert api.get(url).status_code == 403
    assert support_agent.get(url).status_code == 403
    assert admin.get(url).status_code == 200


def test_support_staff_keep_the_support_inbox(support_agent):
    assert support_agent.get("/api/admin/support/tickets/").status_code == 200


def test_me_exposes_roles(api, admin):
    assert api.get("/api/me/").json()["is_superuser"] is False
    assert admin.get("/api/me/").json()["is_superuser"] is True


def test_overview_counts(admin, jane, make_user):
    make_user("bob@example.com")
    pro = Product.objects.get(code="pro")
    Payment.objects.create(user=jane, product=pro, provider="fake", amount=49900, currency="INR",
                           status="successful", refunded_amount=9900, paid_at=timezone.now())
    stats = admin.get("/api/admin/overview/").json()
    assert stats["registrations"] == 2  # staff excluded
    assert stats["completed_profiles"] == 1
    assert stats["payments_successful"] == 1
    assert stats["revenue"] == [{"currency": "INR", "amount": 40000}]
    assert sum(d["count"] for d in stats["signups_by_day"]) == 2


def test_user_search_and_filters(admin, jane, make_user):
    make_user("bob@example.com")
    assert admin.get("/api/admin/users/?search=jane").json()["count"] == 1
    assert admin.get("/api/admin/users/?search=Jane Doe").json()["count"] == 1
    assert admin.get("/api/admin/users/?profile=no").json()["count"] == 1
    act(admin, jane, "grant_pro")
    rows = admin.get("/api/admin/users/?pro=yes").json()["results"]
    assert [r["email"] for r in rows] == ["jane@example.com"] and rows[0]["is_pro"] is True


def test_user_detail(admin, jane):
    body = admin.get(f"/api/admin/users/{jane.pk}/").json()
    assert body["profile"]["full_name"] == "Jane Doe"
    assert body["website_detail"]["admin_blocked"] is False
    assert body["support"] == {"total": 0, "open": 0}
    assert admin.get(f"/api/admin/users/{admin.user.pk}/").status_code == 404  # staff aren't listed


def test_suspend_takes_everything_offline_and_reactivate_restores(admin, api, jane):
    employer = EmployerProfileService.update(EmployerProfileService.get_or_create(jane), {"enabled": True})
    EntitlementService.grant(jane, ["website_publish"], None)
    api.put("/api/website/", {"slug": "jane-doe"}, format="json")
    assert api.post("/api/website/publish/").status_code == 200

    assert act(admin, jane, "suspend", "Spam").status_code == 200
    jane.refresh_from_db()
    assert jane.is_active is False
    assert APIClient().get(f"/api/public/p/{employer.token}/").status_code == 404
    assert APIClient().get("/api/public/sites/jane-doe/").status_code == 404
    session_client = APIClient()
    session_client.force_login(jane)  # an existing session no longer authenticates
    assert session_client.get("/api/me/").status_code == 403

    act(admin, jane, "reactivate", "Appeal accepted")
    assert APIClient().get(f"/api/public/p/{employer.token}/").status_code == 200
    assert APIClient().get("/api/public/sites/jane-doe/").status_code == 200


def test_disable_ai_profile_cannot_be_overridden_by_the_candidate(admin, api, jane):
    employer = EmployerProfileService.update(EmployerProfileService.get_or_create(jane), {"enabled": True})
    act(admin, jane, "disable_ai_profile", "Abusive content")
    assert APIClient().get(f"/api/public/p/{employer.token}/").status_code == 404
    settings_body = api.put("/api/employer-profile/", {"enabled": True}, format="json").json()
    assert settings_body["admin_disabled"] is True and settings_body["admin_disabled_reason"] == "Abusive content"
    assert APIClient().get(f"/api/public/p/{employer.token}/").status_code == 404
    act(admin, jane, "enable_ai_profile")
    assert APIClient().get(f"/api/public/p/{employer.token}/").status_code == 200


def test_take_site_offline_blocks_publishing(admin, api, jane):
    EntitlementService.grant(jane, ["website_publish"], None)
    api.put("/api/website/", {"slug": "jane-doe"}, format="json")
    api.post("/api/website/publish/")

    act(admin, jane, "take_site_offline", "Policy violation")
    assert APIClient().get("/api/public/sites/jane-doe/").status_code == 404
    body = api.get("/api/website/").json()
    assert body["admin_blocked"] is True and "Publishing is disabled by an administrator." in body["publish_problems"]
    assert api.post("/api/website/publish/").status_code == 409

    act(admin, jane, "allow_publishing")
    assert api.post("/api/website/publish/").status_code == 200


def test_grant_and_revoke_pro(admin, api, jane):
    act(admin, jane, "grant_pro", "Comp account")
    assert EntitlementService.active_codes(jane) == {"website_publish", "premium_templates"}
    ent = jane.entitlements.first()
    assert ent.source == "admin" and ent.granted_by == admin.user and ent.reason == "Comp account"

    api.put("/api/website/", {"slug": "jane-doe"}, format="json")
    api.post("/api/website/publish/")
    act(admin, jane, "revoke_pro", "Comp ended")
    assert not EntitlementService.active_codes(jane)
    assert Website.objects.get(user=jane).published_version is None
    assert act(admin, jane, "revoke_pro").status_code == 400  # nothing left to revoke


def test_actions_need_a_reason_and_never_touch_staff(admin, jane, support_agent):
    assert act(admin, jane, "suspend", "   ").status_code == 400
    staff_user = support_agent.handler._force_user
    assert admin.post(f"/api/admin/users/{staff_user.pk}/actions/", {"action": "suspend", "reason": "x"}, format="json").status_code == 404
    assert act(admin, jane, "nonsense").status_code == 400


def test_admin_actions_and_events_are_audited(admin, api, jane):
    act(admin, jane, "grant_pro", "Comp account")
    entry = AuditLog.objects.get(action="admin.grant_pro")
    assert entry.actor == admin.user and entry.subject_user == jane and entry.actor_type == "admin"
    assert entry.metadata["reason"] == "Comp account"
    assert AuditLog.objects.filter(action="profile.updated", subject_user=jane).exists()

    timeline = admin.get(f"/api/admin/users/{jane.pk}/").json()["audit"]
    assert {e["action"] for e in timeline} >= {"admin.grant_pro", "profile.updated"}
    assert admin.get("/api/admin/audit/?action=admin.").json()["count"] == 1
    assert admin.get("/api/admin/audit/?user=jane").json()["count"] >= 2


def test_audit_never_stores_content_and_never_breaks_the_action(admin, jane):
    from apps.audit.services import record

    record("test.event", subject_user=jane, body="secret resume text", job_description="secret jd", safe="ok")
    assert AuditLog.objects.get(action="test.event").metadata == {"safe": "ok"}

    with mock.patch("apps.audit.models.AuditLog.objects.create", side_effect=RuntimeError("db hiccup")):
        assert act(admin, jane, "grant_pro", "Still works").status_code == 200
    assert EntitlementService.has(jane, "website_publish")


def test_login_is_audited(jane, client):
    jane.set_password("S3cure-pass-123")
    jane.save()
    client.post("/_allauth/browser/v1/auth/login", {"email": "jane@example.com", "password": "S3cure-pass-123"}, content_type="application/json")
    client.post("/_allauth/browser/v1/auth/login", {"email": "jane@example.com", "password": "wrong"}, content_type="application/json")
    assert AuditLog.objects.filter(action="auth.login", subject_user=jane).count() == 1
    failed = AuditLog.objects.get(action="auth.login_failed")
    assert failed.metadata == {"email_domain": "example.com"}


def test_template_catalog_controls_the_editor(admin, api, jane):
    admin.patch("/api/admin/templates/", {"key": "executive", "enabled": False}, format="json")
    keys = [t["key"] for t in api.get("/api/website/catalog/").json()["templates"]]
    assert "executive" not in keys
    assert api.put("/api/website/", {"template": "executive"}, format="json").status_code == 400

    admin.patch("/api/admin/templates/", {"key": "minimal", "premium": True, "name": "Minimal Pro",
                                         "default_sections": ["experience", "about"]}, format="json")
    minimal = next(t for t in api.get("/api/website/catalog/").json()["templates"] if t["key"] == "minimal")
    assert minimal == {"key": "minimal", "name": "Minimal Pro", "description": minimal["description"],
                       "sections": ["experience", "about"], "premium": True}
    body = api.put("/api/website/", {"template": "minimal"}, format="json").json()
    assert [s["key"] for s in body["sections"]] == ["experience", "about"]

    bad = admin.patch("/api/admin/templates/", {"key": "minimal", "default_sections": ["github"]}, format="json")
    assert bad.status_code == 400

    versions = admin.get("/api/admin/templates/versions/").json()
    assert versions["count"] == 2
    admin.post("/api/admin/templates/versions/1/restore/")
    restored = {t["key"]: t for t in admin.get("/api/admin/templates/").json()}
    assert restored["executive"]["enabled"] is False and restored["minimal"]["premium"] is False
    assert AuditLog.objects.filter(action="admin.template_catalog_restored").exists()


def test_at_least_one_template_stays_enabled(admin):
    for key in ["executive", "modern", "technical", "creative"]:
        admin.patch("/api/admin/templates/", {"key": key, "enabled": False}, format="json")
    response = admin.patch("/api/admin/templates/", {"key": "minimal", "enabled": False}, format="json")
    assert response.status_code == 400


def test_payments_list_and_filters(admin, jane):
    pro = Product.objects.get(code="pro")
    Payment.objects.create(user=jane, product=pro, provider="razorpay", amount=49900, currency="INR",
                           status="refunded", refunded_amount=49900, provider_order_id="order_1")
    Payment.objects.create(user=jane, product=pro, provider="razorpay", amount=49900, currency="INR", status="failed",
                           provider_order_id="order_2")
    rows = admin.get("/api/admin/payments/?status=refunded").json()["results"]
    assert len(rows) == 1 and rows[0]["refund_status"] == "full" and rows[0]["user_email"] == "jane@example.com"
    assert admin.get("/api/admin/payments/?search=order_2").json()["count"] == 1
    assert admin.get("/api/admin/payments/?from=2000-01-01&to=2000-01-02").json()["count"] == 0


def test_ai_jobs_summary_reports_failures_and_stuck_jobs(admin, api, jane):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from .files import text_pdf

    with mock.patch("apps.resume_parser.tasks.process_resume.delay"):
        upload = api.post("/api/resumes/", {"file": SimpleUploadedFile("cv.pdf", text_pdf())}, format="multipart").json()
    from apps.resume_parser.services import ResumeProcessingService

    ResumeProcessingService.mark_failed(upload["id"], "ai_error")
    with mock.patch("apps.resume_parser.tasks.process_resume.delay"):
        second = api.post("/api/resumes/", {"file": SimpleUploadedFile("cv2.pdf", text_pdf())}, format="multipart").json()
    ResumeParseJob.objects.filter(pk=second["id"]).update(created_at=timezone.now() - timedelta(hours=1))

    summary = admin.get("/api/admin/ai-jobs/").json()
    parsing = next(p for p in summary["pipelines"] if p["key"] == "resume_parsing")
    assert parsing["counts"] == {"failed": 1, "pending": 1}
    assert parsing["stuck"] == 1
    assert parsing["failures"][0]["user_email"] == "jane@example.com" and parsing["failures"][0]["error_code"] == "ai_error"
    assert AuditLog.objects.filter(action="ai.resume_parse_failed", subject_user=jane).exists()
    assert AuditLog.objects.filter(action="resume.uploaded", subject_user=jane).count() == 2
