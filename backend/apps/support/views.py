from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .models import SupportAttachment
from .serializers import (
    CreateTicketSerializer,
    MessageSerializer,
    ReplySerializer,
    StaffReplySerializer,
    StaffTicketSummarySerializer,
    StaffUpdateSerializer,
    TicketSummarySerializer,
)
from .services import StaffSupportService, SupportError, SupportService

PARSERS = [MultiPartParser, FormParser, JSONParser]


class TicketThrottle(UserRateThrottle):
    """Limits opening tickets only; listing them (GET on the same URL) isn't counted."""

    scope = "support_ticket"

    def allow_request(self, request, view):
        return request.method != "POST" or super().allow_request(request, view)


class ReplyThrottle(UserRateThrottle):
    scope = "support_reply"


class Pagination(PageNumberPagination):
    page_size = 25


def _error(exc: SupportError):
    if exc.status == 404:
        raise Http404
    return Response({"detail": exc.message}, status=exc.status)


def _ticket_body(ticket, messages, *, staff: bool):
    summary = (StaffTicketSummarySerializer if staff else TicketSummarySerializer)(ticket).data
    return {
        **summary,
        "description": ticket.description,
        "messages": MessageSerializer(messages, many=True, context={"candidate_view": not staff}).data,
    }


# ----- candidate ------------------------------------------------------------

@api_view(["GET", "POST"])
@parser_classes(PARSERS)
@throttle_classes([TicketThrottle])
def tickets(request):
    if request.method == "GET":
        paginator = Pagination()
        page = paginator.paginate_queryset(SupportService.list_for(request.user), request)
        return paginator.get_paginated_response(TicketSummarySerializer(page, many=True).data)
    serializer = CreateTicketSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        ticket = SupportService.create_ticket(request.user, **serializer.validated_data, files=request.FILES.getlist("files"))
    except SupportError as exc:
        return _error(exc)
    return Response(_ticket_body(ticket, SupportService.visible_messages(ticket), staff=False), status=status.HTTP_201_CREATED)


@api_view(["GET"])
def ticket_detail(request, number):
    try:
        ticket = SupportService.get_for(request.user, number)
    except SupportError as exc:
        return _error(exc)
    SupportService.mark_read(ticket)
    return Response(_ticket_body(ticket, SupportService.visible_messages(ticket), staff=False))


@api_view(["POST"])
@parser_classes(PARSERS)
@throttle_classes([ReplyThrottle])
def ticket_reply(request, number):
    serializer = ReplySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        ticket = SupportService.get_for(request.user, number)
        SupportService.reply(request.user, ticket, body=serializer.validated_data["body"], files=request.FILES.getlist("files"))
    except SupportError as exc:
        return _error(exc)
    ticket.refresh_from_db()
    return Response(_ticket_body(ticket, SupportService.visible_messages(ticket), staff=False), status=status.HTTP_201_CREATED)


@api_view(["POST"])
def ticket_close(request, number):
    try:
        ticket = SupportService.close(request.user, SupportService.get_for(request.user, number))
    except SupportError as exc:
        return _error(exc)
    return Response(_ticket_body(ticket, SupportService.visible_messages(ticket), staff=False))


@api_view(["GET"])
def attachment(request, attachment_id):
    """Stream an attachment to the ticket's candidate or to staff, with safe headers."""
    item = SupportAttachment.objects.select_related("message__ticket").filter(pk=attachment_id).first()
    if item is None:
        raise Http404
    message, ticket = item.message, item.message.ticket
    allowed = request.user.is_staff or (
        ticket.candidate_id == request.user.pk and message.kind in ("candidate", "staff", "event")
    )
    if not allowed:
        raise Http404
    inline = item.content_type.startswith("image/")
    response = FileResponse(
        item.file.open("rb"), content_type=item.content_type, as_attachment=not inline, filename=item.original_name
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src 'self'"
    response["Cache-Control"] = "private, no-store"
    return response


# ----- staff ----------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAdminUser])
def staff_tickets(request):
    p = request.query_params
    qs = StaffSupportService.inbox(
        request.user,
        status=p.get("status") or None,
        priority=p.get("priority") or None,
        assignee=p.get("assignee") or None,
        unread=p.get("unread") in ("1", "true"),
        search=(p.get("search") or "").strip()[:100] or None,
    )
    paginator = Pagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(StaffTicketSummarySerializer(page, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAdminUser])
def staff_ticket(request, number):
    try:
        ticket = StaffSupportService.get(number)
        if request.method == "PATCH":
            serializer = StaffUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            ticket = StaffSupportService.update(
                request.user,
                ticket,
                status=data.get("status"),
                priority=data.get("priority"),
                assigned_to=data["assigned_to"] if "assigned_to" in data else "unchanged",
            )
        else:
            StaffSupportService.mark_read(ticket)
    except SupportError as exc:
        return _error(exc)
    ticket = StaffSupportService.get(number)
    return Response(_ticket_body(ticket, StaffSupportService.messages(ticket), staff=True))


@api_view(["POST"])
@permission_classes([IsAdminUser])
@parser_classes(PARSERS)
def staff_reply(request, number):
    serializer = StaffReplySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        ticket = StaffSupportService.get(number)
        StaffSupportService.reply(
            request.user, ticket, body=data["body"], internal=data["internal"], status=data.get("status"),
            files=request.FILES.getlist("files"),
        )
    except SupportError as exc:
        return _error(exc)
    ticket = StaffSupportService.get(number)
    return Response(_ticket_body(ticket, StaffSupportService.messages(ticket), staff=True), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def staff_users(request):
    return Response(
        [{"id": u.pk, "email": u.email, "name": u.get_full_name() or u.email} for u in StaffSupportService.staff_users()]
    )
