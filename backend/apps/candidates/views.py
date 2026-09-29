from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import CandidateDashboardService


@api_view(["GET"])
def me(request):
    user = request.user
    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "dashboard": CandidateDashboardService.get_state(user),
        }
    )
