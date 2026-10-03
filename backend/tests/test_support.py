import io
from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.support.models import SupportMessage, SupportTicket
from apps.support.notifications import send_for_message

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n%fake\n"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(make_user):
    user = make_user("agent@example.com")
    user.is_staff = True
    user.first_name = "Priya"
    user.save()
    client = APIClient()
    client.force_authenticate(user)
    client.user = user
    return client


def upload(name, data, content_type="application/octet-stream"):
    return SimpleUploadedFile(name, data, content_type=content_type)


def open_ticket(api, **extra):
    body = {"subject": "Can't publish", "description": "The publish button is greyed out.", "priority": "high", **extra}
    with mock.patch("apps.support.tasks.send_support_email.delay"):
        return api.post("/api/support/tickets/", body, format="multipart")


def number_of(response):
    return response.json()["number"]


def test_candidate_opens_a_ticket_with_attachments(api, user):
    response = open_ticket(api, files=[upload("shot.png", PNG), upload("receipt.pdf", PDF)])
    assert response.status_code == 201
    body = response.json()
    assert body["number"].startswith("SUP-") and body["status"] == "open" and body["priority"] == "high"
    first = body["messages"][0]
    assert first["kind"] == "candidate" and first["author"]["name"] == "You"
    assert {a["content_type"] for a in first["attachments"]} == {"image/png", "application/pdf"}

    listed = api.get("/api/support/tickets/").json()
    assert listed["count"] == 1 and listed["results"][0]["unread"] is False


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ([upload("evil.png", b"MZ\x90\x00 not an image")], "isn't a PNG"),
        ([upload("big.png", PNG + b"\x00" * (5 * 1024 * 1024))], "larger than 5 MB"),
        ([upload(f"{i}.png", PNG) for i in range(4)], "at most 3"),
    ],
)
def test_bad_attachments_are_rejected_and_nothing_is_created(api, files, message):
    response = open_ticket(api, files=files)
    assert response.status_code == 400 and message in response.json()["detail"]
    assert not SupportTicket.objects.exists()


def test_candidates_cannot_pick_urgent(api):
    assert open_ticket(api, priority="urgent").status_code == 400


def test_full_conversation_flow(api, user, staff):
    number = number_of(open_ticket(api))

    with mock.patch("apps.support.tasks.send_support_email.delay"):
        staff.patch(f"/api/admin/support/tickets/{number}/", {"assigned_to": staff.user.pk, "status": "in_progress"}, format="json")
        staff.post(f"/api/admin/support/tickets/{number}/messages/", {"body": "Customer seems to be on the free plan.", "internal": True}, format="multipart")
        reply = staff.post(f"/api/admin/support/tickets/{number}/messages/", {"body": "Publishing needs Pro. Want a hand?"}, format="multipart")
    assert reply.json()["status"] == "waiting_for_user"
    assert reply.json()["assigned_to"]["email"] == "agent@example.com"

    # The candidate sees the reply and status changes, never internal notes or assignment/priority changes.
    assert api.get("/api/me/").json()["support_unread"] == 1
    view = api.get(f"/api/support/tickets/{number}/").json()
    kinds = [m["kind"] for m in view["messages"]]
    assert "internal" not in kinds
    assert "free plan" not in str(view) and "Assigned" not in str(view)
    staff_msg = next(m for m in view["messages"] if m["kind"] == "staff")
    assert staff_msg["author"] == {"name": "Priya", "staff": True}
    assert api.get("/api/me/").json()["support_unread"] == 0  # opening it marks it read

    # A candidate reply reopens it and shows as unread for staff.
    with mock.patch("apps.support.tasks.send_support_email.delay"):
        after = api.post(f"/api/support/tickets/{number}/messages/", {"body": "Yes please!"}, format="multipart").json()
    assert after["status"] == "open"
    assert staff.get("/api/me/").json()["staff_support_unread"] == 1
    assert staff.get("/api/admin/support/tickets/?unread=1").json()["count"] == 1

    staff_view = staff.get(f"/api/admin/support/tickets/{number}/").json()
    assert "internal" in [m["kind"] for m in staff_view["messages"]]
    assert staff.get("/api/me/").json()["staff_support_unread"] == 0

    with mock.patch("apps.support.tasks.send_support_email.delay"):
        staff.patch(f"/api/admin/support/tickets/{number}/", {"status": "resolved"}, format="json")
        closed = api.post(f"/api/support/tickets/{number}/close/").json()
    assert closed["status"] == "closed"
    with mock.patch("apps.support.tasks.send_support_email.delay"):
        refused = api.post(f"/api/support/tickets/{number}/messages/", {"body": "One more thing"}, format="multipart")
    assert refused.status_code == 409


def test_tickets_and_attachments_are_private(api, make_user, staff):
    response = open_ticket(api, files=[upload("shot.png", PNG)])
    number = response.json()["number"]
    attachment_url = response.json()["messages"][0]["attachments"][0]["url"]

    other = APIClient()
    other.force_authenticate(make_user("mallory@example.com"))
    assert other.get(f"/api/support/tickets/{number}/").status_code == 404
    assert other.post(f"/api/support/tickets/{number}/messages/", {"body": "hi"}, format="multipart").status_code == 404
    assert other.get(attachment_url).status_code == 404
    assert other.get("/api/support/tickets/").json()["count"] == 0
    # Candidates can't use staff endpoints.
    assert api.get("/api/admin/support/tickets/").status_code == 403
    assert api.patch(f"/api/admin/support/tickets/{number}/", {"status": "closed"}, format="json").status_code == 403

    owner = api.get(attachment_url)
    assert owner.status_code == 200 and b"".join(owner.streaming_content) == PNG
    assert owner["X-Content-Type-Options"] == "nosniff" and "sandbox" in owner["Content-Security-Policy"]
    assert staff.get(attachment_url).status_code == 200


def test_internal_note_attachments_are_staff_only(api, staff):
    number = number_of(open_ticket(api))
    with mock.patch("apps.support.tasks.send_support_email.delay"):
        body = staff.post(
            f"/api/admin/support/tickets/{number}/messages/",
            {"body": "screenshot of admin view", "internal": True, "files": [upload("admin.png", PNG)]},
            format="multipart",
        ).json()
    url = next(m for m in body["messages"] if m["kind"] == "internal")["attachments"][0]["url"]
    assert api.get(url).status_code == 404
    assert staff.get(url).status_code == 200


def test_pdfs_download_instead_of_rendering_inline(api):
    response = open_ticket(api, files=[upload("receipt.pdf", PDF)])
    url = response.json()["messages"][0]["attachments"][0]["url"]
    assert api.get(url)["Content-Disposition"].startswith("attachment")


def test_assignee_must_be_staff(api, staff, user):
    number = number_of(open_ticket(api))
    response = staff.patch(f"/api/admin/support/tickets/{number}/", {"assigned_to": user.pk}, format="json")
    assert response.status_code == 400


def test_inbox_filters(api, staff):
    number = number_of(open_ticket(api))
    open_ticket(api, subject="Billing question")
    staff.patch(f"/api/admin/support/tickets/{number}/", {"assigned_to": staff.user.pk}, format="json")
    assert staff.get("/api/admin/support/tickets/?assignee=me").json()["count"] == 1
    assert staff.get("/api/admin/support/tickets/?assignee=unassigned").json()["count"] == 1
    assert staff.get("/api/admin/support/tickets/?search=billing").json()["count"] == 1
    assert staff.get(f"/api/admin/support/tickets/?search={number}").json()["count"] == 1
    assert staff.get("/api/admin/support/tickets/?priority=high").json()["count"] == 2
    assert staff.get("/api/admin/support/tickets/?status=active").json()["count"] == 2


def test_emails_go_to_the_right_people_once(api, user, staff, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.SUPPORT_NOTIFY_EMAILS = []
    number = number_of(open_ticket(api))
    ticket = SupportTicket.objects.get(number=number)

    first = ticket.messages.get(kind="candidate")
    assert send_for_message(first.pk) == "sent"
    assert send_for_message(first.pk) == "skipped"  # idempotent
    assert mail.outbox[0].to == ["agent@example.com"] and "New request" in mail.outbox[0].subject

    # Send exactly what the app queues (as the Celery worker would).
    with mock.patch("apps.support.tasks.send_support_email.delay", side_effect=send_for_message) as queued, mock.patch(
        "apps.support.services.transaction.on_commit", side_effect=lambda fn: fn()
    ):
        staff.post(f"/api/admin/support/tickets/{number}/messages/", {"body": "secret staff note", "internal": True}, format="multipart")
        staff.post(f"/api/admin/support/tickets/{number}/messages/", {"body": "Here's the fix."}, format="multipart")
    assert queued.call_count == 1  # the public reply only: no internal note, no "waiting for user" event
    candidate_mail = [m for m in mail.outbox if m.to == ["jane@example.com"]]
    assert len(candidate_mail) == 1 and "Here's the fix." in candidate_mail[0].body
    assert all("secret staff note" not in m.body for m in mail.outbox)
    assert "/support/" + number in candidate_mail[0].body


def test_notifications_are_queued_after_commit(api, django_capture_on_commit_callbacks):
    with mock.patch("apps.support.tasks.send_support_email.delay") as delay, django_capture_on_commit_callbacks(execute=True):
        api.post("/api/support/tickets/", {"subject": "Hi", "description": "Help"}, format="multipart")
    delay.assert_called_once_with(SupportMessage.objects.get().pk)


def test_ticket_creation_is_throttled_but_listing_is_not(api, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "support_ticket": "2/day"},
    }
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]):
        assert open_ticket(api).status_code == 201
        assert open_ticket(api).status_code == 201
        assert open_ticket(api).status_code == 429
        for _ in range(5):
            assert api.get("/api/support/tickets/").status_code == 200
