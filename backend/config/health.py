import logging

import redis
from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_redis():
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    try:
        client.ping()
    finally:
        client.close()


CHECKS = {"database": check_database, "redis": check_redis}


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    body = {}
    for name, check in CHECKS.items():
        try:
            check()
            body[name] = "ok"
        except Exception:
            logger.exception("Health check failed: %s", name)
            body[name] = "error"

    healthy = all(value == "ok" for value in body.values())
    body = {"status": "ok" if healthy else "error", **body}
    return Response(body, status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE)
