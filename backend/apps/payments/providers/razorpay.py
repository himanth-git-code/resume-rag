import hashlib
import hmac
import logging

import requests

from .base import PaymentProvider, PaymentProviderError, ProviderPayment

logger = logging.getLogger(__name__)

API = "https://api.razorpay.com/v1"


def hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class RazorpayProvider(PaymentProvider):
    """Razorpay over its REST API (the official SDK is a thin `requests` wrapper)."""

    name = "razorpay"

    def __init__(self, *, key_id: str, key_secret: str, webhook_secret: str, timeout: float = 15, session=None):
        if not (key_id and key_secret and webhook_secret):
            raise PaymentProviderError("Razorpay keys are not configured")
        self.key_id = key_id
        self.webhook_secret = webhook_secret
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.auth = (key_id, key_secret)

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.session.request(method, f"{API}{path}", timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise PaymentProviderError(f"Razorpay unreachable: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise PaymentProviderError(f"Razorpay error {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderError("Unexpected Razorpay response") from exc

    def create_order(self, *, amount: int, currency: str, receipt: str, notes: dict) -> str:
        data = self._call("POST", "/orders", json={"amount": amount, "currency": currency, "receipt": receipt, "notes": notes})
        return data["id"]

    def fetch_order_payments(self, order_id: str) -> list[ProviderPayment]:
        data = self._call("GET", f"/orders/{order_id}/payments")
        return [to_payment(item) for item in data.get("items", [])]

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        return bool(signature) and hmac.compare_digest(hmac_hex(self.webhook_secret, raw_body), signature)

    def checkout_options(self, *, order_id: str, amount: int, currency: str, name: str, email: str) -> dict:
        return {"key": self.key_id, "order_id": order_id, "amount": amount, "currency": currency, "name": name,
                "prefill": {"email": email}}


def to_payment(entity: dict) -> ProviderPayment:
    return ProviderPayment(
        id=entity.get("id", ""),
        order_id=entity.get("order_id") or "",
        amount=int(entity.get("amount") or 0),
        currency=entity.get("currency") or "",
        status=entity.get("status") or "",
        amount_refunded=int(entity.get("amount_refunded") or 0),
        error=(entity.get("error_description") or "")[:300],
    )
