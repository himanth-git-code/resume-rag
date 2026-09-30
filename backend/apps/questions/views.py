from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .models import Question
from .sections import ProfileItems
from .serializers import GenerateSerializer, GenerationSerializer, QuestionSerializer
from .services import GenerationInProgress, InvalidScope, NoProfile, QuestionGenerationService, QuestionQueryService


class GenerateThrottle(UserRateThrottle):
    scope = "question_generate"


class QuestionPagination(PageNumberPagination):
    page_size = 20


@api_view(["GET"])
def question_list(request):
    params = request.query_params
    category = params.get("category") or None
    difficulty = params.get("difficulty") or None
    if category and category not in Question.Category.values:
        return Response({"detail": "Unknown category."}, status=status.HTTP_400_BAD_REQUEST)
    if difficulty and difficulty not in Question.Difficulty.values:
        return Response({"detail": "Unknown difficulty."}, status=status.HTTP_400_BAD_REQUEST)

    qs = QuestionQueryService.list(
        request.user,
        category=category,
        source=params.get("source") or None,
        difficulty=difficulty,
        search=(params.get("search") or "").strip()[:200] or None,
    )
    paginator = QuestionPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(QuestionSerializer(page, many=True).data)


@api_view(["GET"])
def facets(request):
    return Response(QuestionQueryService.facets(request.user))


@api_view(["GET"])
def latest_generation(request):
    gen = QuestionGenerationService.latest(request.user)
    return Response(
        {
            "generation": GenerationSerializer(gen).data if gen else None,
            "has_profile": ProfileItems(request.user).exists,
            "profile_changed": QuestionGenerationService.profile_changed(request.user),
        }
    )


@api_view(["POST"])
@throttle_classes([GenerateThrottle])
def generate(request):
    serializer = GenerateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        if data["kind"] == "full":
            gen = QuestionGenerationService.start_full(request.user)
        else:
            gen = QuestionGenerationService.start_more(
                request.user, category=data.get("category") or None, source=data.get("source") or None
            )
    except NoProfile:
        return Response({"detail": "Save your profile first."}, status=status.HTTP_409_CONFLICT)
    except GenerationInProgress:
        return Response({"detail": "Questions are already being generated."}, status=status.HTTP_409_CONFLICT)
    except InvalidScope as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(GenerationSerializer(gen).data, status=status.HTTP_202_ACCEPTED)
