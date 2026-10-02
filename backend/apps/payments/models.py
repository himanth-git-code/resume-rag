"""One-time payments and the entitlements they grant (SPEC §14).

Paid access is decided only by Entitlement rows, which only webhook (or
server-side reconciliation) processing creates. Never by the frontend.
"""

import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q


class Product(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    # Smallest currency unit (paise for INR).
    price_amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    entitlements = models.JSONField(default=list)
    features = models.JSONField(default=list, help_text="Human-readable feature list for the pricing page")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


def new_public_id() -> str:
    return secrets.token_urlsafe(16)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INITIATED = "initiated", "Initiated"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="payments")
    public_id = models.CharField(max_length=32, unique=True, default=new_public_id)
    provider = models.CharField(max_length=20)
    provider_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    # Snapshot of the price at checkout; webhooks must match it exactly.
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    # Cumulative refunded amount as reported by the provider.
    refunded_amount = models.PositiveIntegerField(default=0)
    failure_reason = models.CharField(max_length=300, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    last_reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class Entitlement(models.Model):
    class Code(models.TextChoices):
        WEBSITE_PUBLISH = "website_publish", "Publish website"
        PREMIUM_TEMPLATES = "premium_templates", "Premium templates"
        WEBSITE_DOWNLOAD = "website_download", "Download website"
        EMPLOYER_AI_PROFILE = "employer_ai_profile", "Employer AI profile"
        PRIORITY_SUPPORT = "priority_support", "Priority support"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entitlements")
    code = models.CharField(max_length=40, choices=Code.choices)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="entitlements")
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "code"], condition=Q(revoked_at__isnull=True), name="one_active_entitlement_per_code"
            )
        ]


class WebhookEvent(models.Model):
    """Every webhook delivery we accepted; the unique event id makes processing idempotent."""

    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=60)
    payload_sha256 = models.CharField(max_length=64)
    outcome = models.CharField(max_length=60, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "event_id"], name="unique_webhook_event")]
