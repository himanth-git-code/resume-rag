from abc import ABC, abstractmethod
from dataclasses import dataclass


class PaymentProviderError(Exception):
    """The provider couldn't be reached or rejected the request. Message is safe to log."""


@dataclass(frozen=True)
class ProviderPayment:
    """A provider-side payment, normalised for our state machine."""

    id: str
    order_id: str
    amount: int
    currency: str
    status: str  # "captured" | "failed" | other provider states
    amount_refunded: int = 0
    error: str = ""


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_order(self, *, amount: int, currency: str, receipt: str, notes: dict) -> str:
        """Create an order and return its provider id."""

    @abstractmethod
    def fetch_order_payments(self, order_id: str) -> list[ProviderPayment]:
        """Payments attempted against an order (for reconciliation)."""

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Whether `signature` authenticates `raw_body`."""

    @abstractmethod
    def checkout_options(self, *, order_id: str, amount: int, currency: str, name: str, email: str) -> dict:
        """Public options for the browser checkout. Must never contain secrets."""
