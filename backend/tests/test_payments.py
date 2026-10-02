import json
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.candidates.services import CandidateProfileService
from apps.payments.models import Entitlement, Payment, WebhookEvent
from apps.payments.providers import ProviderPayment
from apps.payments.providers.razorpay import RazorpayProvider, hmac_hex
from apps.payments.services import EntitlementService, PaymentService
from apps.websites.models import Website

WEBHOOK_SECRET = "whsec_test"
WEBHOOK_URL = "/api/payments/webhooks/razorpay/"


@pytest.fixture
def razorpay(settings):
    settings.PAYMENT_PROVIDER = "razorpay"
    settings.RAZORPAY_KEY_ID = "rzp_test_key"
    settings.RAZORPAY_KEY_SECRET = "rzp_test_secret"
    settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
    with mock.patch.object(RazorpayProvider, "create_order", side_effect=lambda **kw: f"order_{kw['receipt']}"):
        yield


@pytest.fixture
def payment(api, razorpay):
    body = api.post("/api/payments/checkout/", {"product": "pro"}, format="json").json()
    return Payment.objects.get(public_id=body["payment"]["id"])


def event(event_type, payment, *, status="captured", amount=None, currency="INR", payment_id="pay_1", **extra):
    entity = {
        "id": payment_id,
        "order_id": payment.provider_order_id,
        "amount": payment.amount if amount is None else amount,
        "currency": currency,
        "status": status,
        **extra,
    }
    return {"event": event_type, "payload": {"payment": {"entity": entity}}}


def deliver(body: dict, event_id="evt_1", secret=WEBHOOK_SECRET, raw=None):
    raw = raw if raw is not None else json.dumps(body).encode()
    return APIClient().post(
        WEBHOOK_URL,
        data=raw,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=hmac_hex(secret, raw),
        HTTP_X_RAZORPAY_EVENT_ID=event_id,
    )


def test_checkout_creates_an_order_without_exposing_secrets(api, user, razorpay):
    response = api.post("/api/payments/checkout/", {"product": "pro"}, format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["payment"]["status"] == "initiated" and body["payment"]["amount"] == 49900
    assert body["checkout"]["key"] == "rzp_test_key" and body["checkout"]["order_id"].startswith("order_")
    assert "rzp_test_secret" not in json.dumps(body) and WEBHOOK_SECRET not in json.dumps(body)

    # A second click reuses the open order instead of creating another.
    again = api.post("/api/payments/checkout/", {"product": "pro"}, format="json").json()
    assert again["payment"]["id"] == body["payment"]["id"]
    assert Payment.objects.count() == 1
    assert api.post("/api/payments/checkout/", {"product": "nope"}, format="json").status_code == 404


def test_captured_webhook_grants_pro_once(api, user, payment):
    assert deliver(event("payment.captured", payment)).json()["outcome"] == "granted"
    assert deliver(event("payment.captured", payment)).json()["outcome"] == "duplicate"  # same event id
    assert deliver(event("order.paid", payment), event_id="evt_2").json()["outcome"] == "already_successful"

    payment.refresh_from_db()
    assert payment.status == "successful" and payment.provider_payment_id == "pay_1" and payment.paid_at
    assert EntitlementService.active_codes(user) == {"website_publish", "premium_templates"}
    assert Entitlement.objects.count() == 2
    assert WebhookEvent.objects.count() == 2
    assert api.get("/api/me/").json()["entitlements"] == ["premium_templates", "website_publish"]
    assert api.post("/api/payments/checkout/", {"product": "pro"}, format="json").status_code == 409


@pytest.mark.parametrize(
    "tamper",
    [
        lambda b: (b, "wrong-secret"),
        lambda b: (b.replace(b"49900", b"100"), None),  # body changed after signing
    ],
)
def test_bad_signatures_are_rejected(user, payment, tamper):
    raw = json.dumps(event("payment.captured", payment)).encode()
    signature = hmac_hex(WEBHOOK_SECRET, raw)
    raw, secret = tamper(raw)
    response = APIClient().post(
        WEBHOOK_URL,
        data=raw,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=hmac_hex(secret, raw) if secret else signature,
        HTTP_X_RAZORPAY_EVENT_ID="evt_x",
    )
    assert response.status_code == 400
    assert not EntitlementService.active_codes(user)
    assert APIClient().post(WEBHOOK_URL, data=raw, content_type="application/json").status_code == 400  # no signature


def test_amount_or_currency_mismatch_does_not_grant(user, payment):
    assert deliver(event("payment.captured", payment, amount=100)).json()["outcome"] == "amount_mismatch"
    assert deliver(event("payment.captured", payment, currency="USD"), event_id="evt_2").json()["outcome"] == "amount_mismatch"
    payment.refresh_from_db()
    assert payment.status == "initiated" and not EntitlementService.active_codes(user)


def test_out_of_order_events(user, payment):
    deliver(event("payment.captured", payment))
    assert deliver(event("payment.failed", payment, status="failed"), event_id="evt_2").json()["outcome"] == "ignored_already_final"
    payment.refresh_from_db()
    assert payment.status == "successful"


def test_failure_then_capture_and_cancel_then_capture(api, user, payment):
    deliver(event("payment.failed", payment, status="failed", error_description="Card declined"))
    payment.refresh_from_db()
    assert payment.status == "failed" and payment.failure_reason == "Card declined"
    deliver(event("payment.captured", payment, payment_id="pay_2"), event_id="evt_2")
    payment.refresh_from_db()
    assert payment.status == "successful"

    # A dismissed checkout can still be completed by a late capture.
    other = Payment.objects.create(user=user, product=payment.product, provider="razorpay", amount=49900,
                                   currency="INR", provider_order_id="order_late", status="initiated")
    api.post(f"/api/payments/{other.public_id}/cancel/")
    other.refresh_from_db()
    assert other.status == "cancelled"
    deliver(event("payment.captured", other, payment_id="pay_3"), event_id="evt_3")
    other.refresh_from_db()
    assert other.status == "successful"


def refund_event(payment, *, refund_amount, cumulative, refund_id="rfnd_1"):
    return {
        "event": "refund.processed",
        "payload": {
            "refund": {"entity": {"id": refund_id, "payment_id": "pay_1", "amount": refund_amount}},
            "payment": {"entity": {"id": "pay_1", "order_id": payment.provider_order_id, "amount": payment.amount,
                                   "currency": "INR", "status": "refunded", "amount_refunded": cumulative}},
        },
    }


def test_partial_refund_keeps_access_full_refund_revokes_and_unpublishes(api, user, payment):
    deliver(event("payment.captured", payment))
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        CandidateProfileService.save(user, {"full_name": "Jane Doe"})
    api.put("/api/website/", {"slug": "jane-doe"}, format="json")
    assert api.post("/api/website/publish/").status_code == 200

    assert deliver(refund_event(payment, refund_amount=10000, cumulative=10000), event_id="evt_r1").json()["outcome"] == "partial_refund"
    assert EntitlementService.has(user, "website_publish")

    outcome = deliver(refund_event(payment, refund_amount=39900, cumulative=49900, refund_id="rfnd_2"), event_id="evt_r2").json()["outcome"]
    assert outcome == "refunded_revoked"
    payment.refresh_from_db()
    assert payment.status == "refunded" and payment.refunded_amount == 49900
    assert not EntitlementService.active_codes(user)
    assert Website.objects.get(user=user).published_version is None
    assert APIClient().get("/api/public/sites/jane-doe/").status_code == 404
    assert "Unlock Pro to publish your site." in api.get("/api/website/").json()["publish_problems"]


def test_reconciliation_grants_when_the_webhook_is_late(api, user, payment):
    remote = [ProviderPayment(id="pay_9", order_id=payment.provider_order_id, amount=49900, currency="INR", status="captured")]
    with mock.patch.object(RazorpayProvider, "fetch_order_payments", return_value=remote) as fetch:
        assert api.get(f"/api/payments/{payment.public_id}/").json()["status"] == "successful"
        api.get(f"/api/payments/{payment.public_id}/")  # already final: no provider call
    assert fetch.call_count == 1
    assert EntitlementService.has(user, "premium_templates")


def test_reconciliation_is_rate_limited(api, payment):
    with mock.patch.object(RazorpayProvider, "fetch_order_payments", return_value=[]) as fetch:
        api.get(f"/api/payments/{payment.public_id}/")
        api.get(f"/api/payments/{payment.public_id}/")
        assert fetch.call_count == 1
        Payment.objects.filter(pk=payment.pk).update(last_reconciled_at=timezone.now() - timedelta(minutes=1))
        api.get(f"/api/payments/{payment.public_id}/")
        assert fetch.call_count == 2


def test_simulate_only_in_debug_with_fake_provider(api, user, settings):
    settings.PAYMENT_PROVIDER = "fake"
    payment_id = api.post("/api/payments/checkout/", {"product": "pro"}, format="json").json()["payment"]["id"]

    settings.DEBUG = False
    assert api.post(f"/api/payments/{payment_id}/simulate/", {"outcome": "success"}, format="json").status_code == 404

    settings.DEBUG = True
    body = api.post(f"/api/payments/{payment_id}/simulate/", {"outcome": "success"}, format="json").json()
    assert body["status"] == "successful"
    assert EntitlementService.has(user, "website_publish")


def test_payments_are_private(api, payment, make_user):
    other = APIClient()
    other.force_authenticate(make_user("mallory@example.com"))
    assert other.get(f"/api/payments/{payment.public_id}/").status_code == 404
    assert other.post(f"/api/payments/{payment.public_id}/cancel/").status_code == 404
    assert other.get("/api/payments/").json()["count"] == 0
    assert api.get("/api/payments/").json()["count"] == 1
    assert APIClient().post("/api/payments/checkout/", {"product": "pro"}, format="json").status_code == 403


def test_premium_templates_need_pro_to_publish(api, user):
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        CandidateProfileService.save(user, {"full_name": "Jane Doe"})
    api.put("/api/website/", {"slug": "jane-doe", "template": "executive"}, format="json")
    assert "Unlock Pro to publish your site." in api.get("/api/website/").json()["publish_problems"]

    EntitlementService.grant(user, ["website_publish"], None)
    assert "This template is part of Pro." in api.get("/api/website/").json()["publish_problems"]
    api.put("/api/website/", {"template": "modern"}, format="json")
    assert api.post("/api/website/publish/").status_code == 200

    catalog = {t["key"]: t["premium"] for t in api.get("/api/website/catalog/").json()["templates"]}
    assert catalog == {"executive": True, "modern": False, "technical": True, "creative": True, "minimal": False}


def test_razorpay_order_request_shape():
    session = mock.Mock()
    session.request.return_value = mock.Mock(status_code=200, json=lambda: {"id": "order_abc"})
    provider = RazorpayProvider(key_id="k", key_secret="s", webhook_secret="w", session=session)

    assert provider.create_order(amount=49900, currency="INR", receipt="r1", notes={"product": "pro"}) == "order_abc"
    method, url = session.request.call_args.args
    assert (method, url) == ("POST", "https://api.razorpay.com/v1/orders")
    assert session.request.call_args.kwargs["json"] == {"amount": 49900, "currency": "INR", "receipt": "r1", "notes": {"product": "pro"}}
    assert session.auth == ("k", "s")
    assert provider.verify_webhook(b"{}", hmac_hex("w", b"{}"))
    assert not provider.verify_webhook(b"{}", "")


def test_provider_outage_is_reported_cleanly(api, settings):
    from apps.payments.providers import PaymentProviderError

    settings.PAYMENT_PROVIDER = "razorpay"
    settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET, settings.RAZORPAY_WEBHOOK_SECRET = "k", "s", "w"
    with mock.patch.object(RazorpayProvider, "create_order", side_effect=PaymentProviderError("down")):
        response = api.post("/api/payments/checkout/", {"product": "pro"}, format="json")
    assert response.status_code == 503 and response.json()["code"] == "provider_unavailable"
