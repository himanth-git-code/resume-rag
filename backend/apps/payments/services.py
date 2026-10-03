"""Payments and entitlements (SPEC §14).

The only paths that change a payment to "successful" (and grant entitlements)
are verified provider webhooks and server-to-server reconciliation. The browser
can start a checkout and ask for status, nothing more.
"""

import hashlib
import json
import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Entitlement, Payment, Product, WebhookEvent
from .providers import PaymentProviderError, ProviderPayment, get_payment_provider
from .providers.razorpay import to_payment
from apps.audit.services import record

logger = logging.getLogger(__name__)

Status = Payment.Status
REUSE_INITIATED_FOR = timedelta(hours=1)
RECONCILE_EVERY = timedelta(seconds=15)


class CheckoutError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class InvalidWebhook(Exception):
    pass


class EntitlementService:
    @staticmethod
    def active_codes(user) -> set[str]:
        return set(Entitlement.objects.filter(user=user, revoked_at__isnull=True).values_list("code", flat=True))

    @staticmethod
    def has(user, code: str) -> bool:
        return Entitlement.objects.filter(user=user, code=code, revoked_at__isnull=True).exists()

    @staticmethod
    def grant(user, codes, payment: Payment | None, *, granted_by=None, reason: str = "") -> None:
        """Idempotent: codes the user already holds are left as they are."""
        source = Entitlement.Source.ADMIN if granted_by is not None else Entitlement.Source.PAYMENT
        for code in codes:
            if not EntitlementService.has(user, code):
                Entitlement.objects.create(
                    user=user, code=code, payment=payment, source=source, granted_by=granted_by, reason=reason[:300]
                )

    @staticmethod
    def revoke_all(user, codes) -> int:
        """End the user's active entitlements for `codes` (any source) and apply the effects."""
        revoked = Entitlement.objects.filter(user=user, code__in=codes, revoked_at__isnull=True).update(revoked_at=timezone.now())
        EntitlementService.apply_revocation_effects(user)
        return revoked

    @staticmethod
    def revoke_for_payment(payment: Payment) -> None:
        Entitlement.objects.filter(payment=payment, revoked_at__isnull=True).update(revoked_at=timezone.now())
        EntitlementService.apply_revocation_effects(payment.user)

    @staticmethod
    def apply_revocation_effects(user) -> None:
        """Bring paid features in line with the user's remaining entitlements."""
        from apps.websites.models import Website
        from apps.websites.services import PublishingService

        website = Website.objects.filter(user=user, published_version__isnull=False).first()
        if website is not None and not EntitlementService.has(user, Entitlement.Code.WEBSITE_PUBLISH):
            PublishingService.unpublish(website)


class PaymentService:
    # ----- checkout ---------------------------------------------------------

    @staticmethod
    def products():
        return Product.objects.filter(active=True).order_by("price_amount")

    @staticmethod
    @transaction.atomic
    def start_checkout(user, product_code: str) -> tuple[Payment, dict]:
        product = Product.objects.filter(code=product_code, active=True).first()
        if product is None:
            raise CheckoutError("unknown_product", "This product isn't available.", status=404)
        if set(product.entitlements) <= EntitlementService.active_codes(user):
            raise CheckoutError("already_owned", "You already have this.", status=409)

        provider = get_payment_provider()
        reusable = (
            Payment.objects.select_for_update()
            .filter(
                user=user,
                product=product,
                provider=provider.name,
                status=Status.INITIATED,
                amount=product.price_amount,
                created_at__gte=timezone.now() - REUSE_INITIATED_FOR,
            )
            .first()
        )
        payment = reusable or Payment.objects.create(
            user=user, product=product, provider=provider.name, amount=product.price_amount, currency=product.currency
        )
        if payment.provider_order_id is None:
            try:
                order_id = provider.create_order(
                    amount=payment.amount,
                    currency=payment.currency,
                    receipt=payment.public_id,
                    notes={"product": product.code, "payment": payment.public_id},
                )
            except PaymentProviderError as exc:
                logger.warning("Checkout order failed for payment %s: %s", payment.pk, exc)
                raise CheckoutError("provider_unavailable", "Payments are unavailable right now. Please try again.", 503) from exc
            payment.provider_order_id = order_id
            payment.status = Status.INITIATED
            payment.save(update_fields=["provider_order_id", "status", "updated_at"])

        options = provider.checkout_options(
            order_id=payment.provider_order_id,
            amount=payment.amount,
            currency=payment.currency,
            name=product.name,
            email=user.email,
        )
        return payment, options

    @staticmethod
    def get_for(user, public_id: str) -> Payment | None:
        return Payment.objects.select_related("product").filter(user=user, public_id=public_id).first()

    @staticmethod
    def cancel(payment: Payment) -> Payment:
        # Only an unfinished checkout can be cancelled; a later capture still wins.
        Payment.objects.filter(pk=payment.pk, status__in=[Status.PENDING, Status.INITIATED]).update(
            status=Status.CANCELLED, updated_at=timezone.now()
        )
        payment.refresh_from_db()
        return payment

    # ----- state changes (webhooks and reconciliation only) ----------------

    @staticmethod
    def _mark_captured(payment: Payment, remote: ProviderPayment) -> str:
        if payment.status == Status.SUCCESSFUL:
            return "already_successful"
        if payment.status == Status.REFUNDED:
            return "ignored_refunded"
        if remote.amount != payment.amount or remote.currency.upper() != payment.currency.upper():
            logger.error("Payment %s: captured amount/currency mismatch", payment.pk)
            payment.failure_reason = "Captured amount or currency did not match the order."
            payment.save(update_fields=["failure_reason", "updated_at"])
            return "amount_mismatch"
        payment.status = Status.SUCCESSFUL
        payment.provider_payment_id = remote.id
        payment.paid_at = timezone.now()
        payment.failure_reason = ""
        payment.save(update_fields=["status", "provider_payment_id", "paid_at", "failure_reason", "updated_at"])
        EntitlementService.grant(payment.user, payment.product.entitlements, payment)
        record("payment.successful", subject_user=payment.user, target=payment, amount=payment.amount, currency=payment.currency)
        return "granted"

    @staticmethod
    def _mark_failed(payment: Payment, remote: ProviderPayment) -> str:
        if payment.status in (Status.SUCCESSFUL, Status.REFUNDED):
            return "ignored_already_final"  # out-of-order delivery: a capture always wins
        payment.status = Status.FAILED
        payment.failure_reason = remote.error or "The payment was declined."
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        record("payment.failed", subject_user=payment.user, target=payment)
        return "failed"

    @staticmethod
    def _mark_refund(payment: Payment, amount_refunded: int) -> str:
        if amount_refunded <= payment.refunded_amount:
            return "refund_already_recorded"
        payment.refunded_amount = amount_refunded
        fields = ["refunded_amount", "updated_at"]
        if amount_refunded >= payment.amount and payment.status == Status.SUCCESSFUL:
            payment.status = Status.REFUNDED
            fields.append("status")
        payment.save(update_fields=fields)
        record("payment.refunded", subject_user=payment.user, target=payment, refunded_amount=amount_refunded,
               full=payment.status == Status.REFUNDED)
        if payment.status == Status.REFUNDED:
            EntitlementService.revoke_for_payment(payment)
            return "refunded_revoked"
        return "partial_refund"

    # ----- webhooks ---------------------------------------------------------

    @staticmethod
    def process_webhook(provider_name: str, raw_body: bytes, signature: str, event_id: str) -> str:
        """Verify, de-duplicate and apply one provider webhook. Returns an outcome label."""
        provider = get_payment_provider(provider_name)
        if not provider.verify_webhook(raw_body, signature):
            raise InvalidWebhook("bad signature")
        try:
            event = json.loads(raw_body)
        except ValueError as exc:
            raise InvalidWebhook("bad json") from exc
        event_type = event.get("event", "")
        event_id = event_id or hashlib.sha256(raw_body).hexdigest()

        with transaction.atomic():
            try:
                with transaction.atomic():
                    record = WebhookEvent.objects.create(
                        provider=provider_name,
                        event_id=event_id,
                        event_type=event_type[:60],
                        payload_sha256=hashlib.sha256(raw_body).hexdigest(),
                    )
            except IntegrityError:
                return "duplicate"

            outcome = PaymentService._apply(event_type, event.get("payload") or {})
            record.outcome = outcome
            record.processed_at = timezone.now()
            record.save(update_fields=["outcome", "processed_at"])
        logger.info("Webhook %s %s: %s", provider_name, event_type, outcome)
        return outcome

    @staticmethod
    def _apply(event_type: str, payload: dict) -> str:
        payment_entity = (payload.get("payment") or {}).get("entity") or {}
        remote = to_payment(payment_entity) if payment_entity else None

        if event_type in ("payment.captured", "order.paid", "payment.failed"):
            order_id = (remote.order_id if remote else "") or ((payload.get("order") or {}).get("entity") or {}).get("id", "")
            payment = Payment.objects.select_for_update().select_related("product", "user").filter(provider_order_id=order_id).first()
            if payment is None or remote is None:
                return "unknown_order"
            if event_type == "payment.failed":
                return PaymentService._mark_failed(payment, remote)
            if remote.status != "captured" and event_type == "payment.captured":
                return "not_captured"
            return PaymentService._mark_captured(payment, remote)

        if event_type == "refund.processed":
            refund = (payload.get("refund") or {}).get("entity") or {}
            payment_id = refund.get("payment_id") or (remote.id if remote else "")
            payment = Payment.objects.select_for_update().select_related("product", "user").filter(provider_payment_id=payment_id).first()
            if payment is None:
                return "unknown_payment"
            # Prefer the provider's cumulative figure; fall back to adding this refund.
            total = remote.amount_refunded if remote and remote.amount_refunded else payment.refunded_amount + int(refund.get("amount") or 0)
            return PaymentService._mark_refund(payment, total)

        return "ignored"

    # ----- reconciliation ---------------------------------------------------

    @staticmethod
    def reconcile(payment: Payment) -> Payment:
        """Ask the provider directly when a webhook hasn't arrived (rate-limited per payment)."""
        if payment.status not in (Status.INITIATED, Status.CANCELLED) or not payment.provider_order_id:
            return payment
        now = timezone.now()
        if payment.last_reconciled_at and now - payment.last_reconciled_at < RECONCILE_EVERY:
            return payment
        Payment.objects.filter(pk=payment.pk).update(last_reconciled_at=now)
        try:
            remote_payments = get_payment_provider(payment.provider).fetch_order_payments(payment.provider_order_id)
        except PaymentProviderError as exc:
            logger.warning("Reconcile failed for payment %s: %s", payment.pk, exc)
            return payment
        with transaction.atomic():
            locked = Payment.objects.select_for_update().select_related("product", "user").get(pk=payment.pk)
            captured = next((p for p in remote_payments if p.status == "captured"), None)
            if captured is not None:
                PaymentService._mark_captured(locked, captured)
            elif remote_payments and all(p.status == "failed" for p in remote_payments) and locked.status == Status.INITIATED:
                PaymentService._mark_failed(locked, remote_payments[-1])
        payment.refresh_from_db()
        return payment
