from rest_framework.permissions import BasePermission


class IsSuperuser(BasePermission):
    """Full admin dashboard. Support-only staff (is_staff) use the support inbox instead."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
