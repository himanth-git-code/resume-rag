import json
import secrets

from django.conf import settings
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .serializers import CheckoutSerializer, PaymentSerializer, ProductSerializer, SimulateSerializer
from .services import CheckoutError, EntitlementService, InvalidWebhook, PaymentService


class CheckoutThrottle(UserRateThrottle):
    scope = "checkout"


def _payment_or_404(request, public_id):
    payment = PaymentService.get_for(request.user, public_id)
    if payment is None:
        raise Http404
    return payment


@api_view(["GET"])
def products(request):
    return Response(ProductSerializer(PaymentService.products(), many=True).data)


@api_view(["GET"])
def entitlements(request):
    return Response({"codes": sorted(EntitlementService.active_codes(request.user)), "provider": settings.PAYMENT_PROVIDER})


@api_view(["POST"])
@throttle_classes([CheckoutThrottle])
def checkout(request):
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        payment, options = PaymentService.start_checkout(request.user, serializer.validated_data["product"])
    except CheckoutError as exc:
        return Response({"code": exc.code, "detail": exc.message}, status=exc.status)
    return Response(
        {"payment": PaymentSerializer(payment).data, "provider": payment.provider, "checkout": options},
        status=status.HTTP_201_CREATED,
    )


class PaymentPagination(PageNumberPagination):
    page_size = 20


@api_view(["GET"])
def payment_list(request):
    paginator = PaymentPagination()
    page = paginator.paginate_queryset(request.user.payments.select_related("product").all(), request)
    return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)


@api_view(["GET"])
def payment_detail(request, public_id):
    # Polled while waiting for the webhook; reconciliation is rate-limited per payment.
    payment = PaymentService.reconcile(_payment_or_404(request, public_id))
    return Response(PaymentSerializer(payment).data)


@api_view(["POST"])
def payment_cancel(request, public_id):
    return Response(PaymentSerializer(PaymentService.cancel(_payment_or_404(request, public_id))).data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """Razorpay webhooks. The signature over the raw body is the only credential."""
    try:
        outcome = PaymentService.process_webhook(
            "razorpay",
            request.body,
            request.headers.get("X-Razorpay-Signature", ""),
            request.headers.get("X-Razorpay-Event-Id", ""),
        )
    except InvalidWebhook:
        return Response({"detail": "invalid webhook"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"outcome": outcome})


@api_view(["POST"])
def simulate(request, public_id):
    """Development only: drive the real webhook path with a locally signed event."""
    if not (settings.DEBUG and settings.PAYMENT_PROVIDER == "fake"):
        raise Http404
    payment = _payment_or_404(request, public_id)
    serializer = SimulateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    success = serializer.validated_data["outcome"] == "success"

    from .providers.fake import FakePaymentProvider

    event = {
        "event": "payment.captured" if success else "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_fake_{secrets.token_hex(6)}",
                    "order_id": payment.provider_order_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "status": "captured" if success else "failed",
                    "error_description": None if success else "Simulated decline",
                }
            }
        },
    }
    body = json.dumps(event).encode()
    PaymentService.process_webhook("fake", body, FakePaymentProvider().sign(body), f"evt_fake_{secrets.token_hex(8)}")
    payment.refresh_from_db()
    return Response(PaymentSerializer(payment).data)
