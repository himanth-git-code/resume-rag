from django.conf import settings

from .base import PaymentProvider, PaymentProviderError, ProviderPayment

__all__ = ["PaymentProvider", "PaymentProviderError", "ProviderPayment", "get_payment_provider"]


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    name = name or settings.PAYMENT_PROVIDER
    if name == "razorpay":
        from .razorpay import RazorpayProvider

        return RazorpayProvider(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
            webhook_secret=settings.RAZORPAY_WEBHOOK_SECRET,
        )
    if name == "fake":
        from .fake import FakePaymentProvider

        return FakePaymentProvider()
    raise PaymentProviderError(f"Unknown PAYMENT_PROVIDER: {name!r}")
