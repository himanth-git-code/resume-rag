from django.db import migrations

PRO = {
    "code": "pro",
    "name": "Pro",
    "description": "One-time unlock. No subscription.",
    "price_amount": 49900,  # ₹499 in paise
    "currency": "INR",
    "entitlements": ["website_publish", "premium_templates"],
    "features": [
        "Publish your personal website at /portfolio/your-name",
        "Premium templates: Executive, Technical and Creative",
    ],
    "active": True,
}


def seed(apps, schema_editor):
    Product = apps.get_model("payments", "Product")
    Product.objects.update_or_create(code=PRO["code"], defaults={k: v for k, v in PRO.items() if k != "code"})


def unseed(apps, schema_editor):
    apps.get_model("payments", "Product").objects.filter(code=PRO["code"], payments__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
