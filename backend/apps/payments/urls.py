from django.urls import path

from . import views

urlpatterns = [
    path("payments/", views.payment_list, name="payments"),
    path("payments/products/", views.products, name="payment-products"),
    path("payments/entitlements/", views.entitlements, name="payment-entitlements"),
    path("payments/checkout/", views.checkout, name="payment-checkout"),
    path("payments/webhooks/razorpay/", views.razorpay_webhook, name="payment-webhook-razorpay"),
    path("payments/<str:public_id>/", views.payment_detail, name="payment-detail"),
    path("payments/<str:public_id>/cancel/", views.payment_cancel, name="payment-cancel"),
    path("payments/<str:public_id>/simulate/", views.simulate, name="payment-simulate"),
]
