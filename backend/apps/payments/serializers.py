from rest_framework import serializers

from .models import Payment, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["code", "name", "description", "price_amount", "currency", "entitlements", "features"]


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id")
    product = serializers.CharField(source="product.code")
    product_name = serializers.CharField(source="product.name")

    class Meta:
        model = Payment
        fields = [
            "id", "product", "product_name", "provider", "amount", "currency", "status",
            "refunded_amount", "failure_reason", "paid_at", "created_at",
        ]


class CheckoutSerializer(serializers.Serializer):
    product = serializers.CharField(max_length=40)


class SimulateSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["success", "failure"])
