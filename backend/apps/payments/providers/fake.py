import secrets

from .base import PaymentProvider, ProviderPayment
from .razorpay import hmac_hex

FAKE_WEBHOOK_SECRET = "fake-webhook-secret"


class FakePaymentProvider(PaymentProvider):
    """Local/dev provider: no network, Razorpay-shaped webhooks signed with a local secret."""

    name = "fake"

    def __init__(self):
        self.orders: dict[str, list[ProviderPayment]] = {}

    def create_order(self, *, amount: int, currency: str, receipt: str, notes: dict) -> str:
        return f"order_fake_{secrets.token_hex(8)}"

    def fetch_order_payments(self, order_id: str) -> list[ProviderPayment]:
        return self.orders.get(order_id, [])

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        return bool(signature) and secrets.compare_digest(hmac_hex(FAKE_WEBHOOK_SECRET, raw_body), signature)

    def sign(self, raw_body: bytes) -> str:
        return hmac_hex(FAKE_WEBHOOK_SECRET, raw_body)

    def checkout_options(self, *, order_id: str, amount: int, currency: str, name: str, email: str) -> dict:
        return {"key": None, "order_id": order_id, "amount": amount, "currency": currency, "name": name,
                "prefill": {"email": email}}
