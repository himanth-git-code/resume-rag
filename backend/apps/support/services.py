from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .models import SupportAttachment, SupportMessage, SupportTicket
from apps.audit.services import record

Status = SupportTicket.Status
Kind = SupportMessage.Kind

MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
CANDIDATE_PRIORITIES = {SupportTicket.Priority.LOW, SupportTicket.Priority.NORMAL, SupportTicket.Priority.HIGH}
# Message kinds a candidate may see.
CANDIDATE_VISIBLE = [Kind.CANDIDATE, Kind.STAFF, Kind.EVENT]


class SupportError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def detect_attachment_type(data: bytes) -> str | None:
    """Content type from the file's bytes (never its name or the browser's claim)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _validated_files(files) -> list[tuple[str, str, bytes]]:
    files = list(files or [])
    if len(files) > MAX_ATTACHMENTS:
        raise SupportError(f"Attach at most {MAX_ATTACHMENTS} files.")
    validated = []
    for f in files:
        if f.size > MAX_ATTACHMENT_BYTES:
            raise SupportError(f"“{f.name}” is larger than 5 MB.")
        data = f.read()
        content_type = detect_attachment_type(data)
        if content_type is None:
            raise SupportError(f"“{f.name}” isn't a PNG, JPEG or PDF.")
        validated.append(((f.name or "attachment")[:255], content_type, data))
    return validated


def _attach(message: SupportMessage, files: list[tuple[str, str, bytes]]) -> None:
    for name, content_type, data in files:
        attachment = SupportAttachment(message=message, original_name=name, content_type=content_type, size=len(data))
        attachment.file.save("upload", ContentFile(data), save=False)
        attachment.save()


def _notify(message: SupportMessage) -> None:
    from .tasks import send_support_email

    transaction.on_commit(lambda: send_support_email.delay(message.pk))


def _event(ticket: SupportTicket, author, text: str, *, notify: bool = False, staff_only: bool = False) -> SupportMessage:
    """Record a change in the thread. Staff-only events (priority, assignment) use the internal kind."""
    kind = Kind.INTERNAL if staff_only else Kind.EVENT
    message = SupportMessage.objects.create(ticket=ticket, author=author, kind=kind, body=text)
    if notify:
        _notify(message)
    return message


def _display(user) -> str:
    return (user.get_full_name() or user.email) if user else "Support"


class SupportService:
    """Candidate side. Every query is scoped to the candidate."""

    @staticmethod
    def list_for(user):
        unread = SupportMessage.objects.filter(ticket=OuterRef("pk"), kind__in=[Kind.STAFF, Kind.EVENT]).exclude(
            author=user
        ).filter(Q(ticket__candidate_last_read_at__isnull=True) | Q(created_at__gt=OuterRef("candidate_last_read_at")))
        return SupportTicket.objects.filter(candidate=user).annotate(unread=Exists(unread))

    @staticmethod
    def unread_count(user) -> int:
        return SupportService.list_for(user).filter(unread=True).count()

    @staticmethod
    def get_for(user, number: str) -> SupportTicket:
        ticket = SupportTicket.objects.filter(candidate=user, number=number).first()
        if ticket is None:
            raise SupportError("Not found.", status=404)
        return ticket

    @staticmethod
    def visible_messages(ticket: SupportTicket):
        return ticket.messages.filter(kind__in=CANDIDATE_VISIBLE).prefetch_related("attachments").select_related("author")

    @staticmethod
    @transaction.atomic
    def create_ticket(user, *, subject: str, description: str, priority: str, files=None) -> SupportTicket:
        if priority not in CANDIDATE_PRIORITIES:
            priority = SupportTicket.Priority.NORMAL
        validated = _validated_files(files)
        ticket = SupportTicket.objects.create(
            candidate=user, subject=subject, description=description, priority=priority, candidate_last_read_at=timezone.now()
        )
        ticket.number = f"SUP-{ticket.pk:06d}"
        ticket.save(update_fields=["number"])
        message = SupportMessage.objects.create(ticket=ticket, author=user, kind=Kind.CANDIDATE, body=description)
        _attach(message, validated)
        _notify(message)
        return ticket

    @staticmethod
    @transaction.atomic
    def reply(user, ticket: SupportTicket, *, body: str, files=None) -> SupportMessage:
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        if ticket.status == Status.CLOSED:
            raise SupportError("This request is closed. Please open a new one.", status=409)
        validated = _validated_files(files)
        message = SupportMessage.objects.create(ticket=ticket, author=user, kind=Kind.CANDIDATE, body=body)
        _attach(message, validated)
        if ticket.status in (Status.WAITING_FOR_USER, Status.RESOLVED):
            ticket.status = Status.OPEN
            _event(ticket, user, "Reopened by the candidate's reply.")
        ticket.candidate_last_read_at = timezone.now()
        ticket.save(update_fields=["status", "candidate_last_read_at", "updated_at"])
        _notify(message)
        return message

    @staticmethod
    @transaction.atomic
    def close(user, ticket: SupportTicket) -> SupportTicket:
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        if ticket.status != Status.CLOSED:
            ticket.status, ticket.closed_at = Status.CLOSED, timezone.now()
            ticket.save(update_fields=["status", "closed_at", "updated_at"])
            _event(ticket, user, "Closed by the candidate.")
        return ticket

    @staticmethod
    def mark_read(ticket: SupportTicket) -> None:
        SupportTicket.objects.filter(pk=ticket.pk).update(candidate_last_read_at=timezone.now())


class StaffSupportService:
    """Staff side (callers must be is_staff)."""

    @staticmethod
    def _with_unread(qs):
        unread = SupportMessage.objects.filter(ticket=OuterRef("pk"), kind=Kind.CANDIDATE).filter(
            Q(ticket__staff_last_read_at__isnull=True) | Q(created_at__gt=OuterRef("staff_last_read_at"))
        )
        return qs.annotate(unread=Exists(unread))

    @staticmethod
    def inbox(staff_user, *, status=None, priority=None, assignee=None, unread=False, search=None):
        qs = StaffSupportService._with_unread(SupportTicket.objects.select_related("candidate", "assigned_to"))
        if status == "active":
            qs = qs.exclude(status__in=[Status.RESOLVED, Status.CLOSED])
        elif status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assignee == "me":
            qs = qs.filter(assigned_to=staff_user)
        elif assignee == "unassigned":
            qs = qs.filter(assigned_to__isnull=True)
        elif assignee and str(assignee).isdigit():
            qs = qs.filter(assigned_to_id=int(assignee))
        if unread:
            qs = qs.filter(unread=True)
        if search:
            qs = qs.filter(Q(number__iexact=search) | Q(subject__icontains=search) | Q(candidate__email__icontains=search))
        return qs

    @staticmethod
    def unread_count() -> int:
        return StaffSupportService._with_unread(SupportTicket.objects.exclude(status=Status.CLOSED)).filter(unread=True).count()

    @staticmethod
    def get(number: str) -> SupportTicket:
        ticket = SupportTicket.objects.select_related("candidate", "assigned_to").filter(number=number).first()
        if ticket is None:
            raise SupportError("Not found.", status=404)
        return ticket

    @staticmethod
    def messages(ticket: SupportTicket):
        return ticket.messages.prefetch_related("attachments").select_related("author")

    @staticmethod
    def staff_users():
        return get_user_model().objects.filter(is_staff=True, is_active=True).order_by("email")

    @staticmethod
    @transaction.atomic
    def reply(staff_user, ticket: SupportTicket, *, body: str, internal: bool, status: str | None = None, files=None) -> SupportMessage:
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        validated = _validated_files(files)
        message = SupportMessage.objects.create(
            ticket=ticket, author=staff_user, kind=Kind.INTERNAL if internal else Kind.STAFF, body=body
        )
        _attach(message, validated)
        ticket.staff_last_read_at = timezone.now()
        ticket.save(update_fields=["staff_last_read_at", "updated_at"])
        if not internal:
            _notify(message)
            # A public reply usually means it's the candidate's turn.
            StaffSupportService._set_status(staff_user, ticket, status or Status.WAITING_FOR_USER)
        elif status:
            StaffSupportService._set_status(staff_user, ticket, status)
        return message

    @staticmethod
    def _set_status(staff_user, ticket: SupportTicket, status: str) -> None:
        if status == ticket.status:
            return
        ticket.status = status
        ticket.closed_at = timezone.now() if status == Status.CLOSED else None
        ticket.save(update_fields=["status", "closed_at", "updated_at"])
        label = Status(status).label
        # Tell the candidate when their request is resolved or closed.
        _event(ticket, staff_user, f"Status changed to {label}.", notify=status in (Status.RESOLVED, Status.CLOSED))
        record("support.status_changed", actor=staff_user, subject_user=ticket.candidate, target=ticket, status=status)

    @staticmethod
    @transaction.atomic
    def update(staff_user, ticket: SupportTicket, *, status=None, priority=None, assigned_to="unchanged") -> SupportTicket:
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        if priority and priority != ticket.priority:
            ticket.priority = priority
            ticket.save(update_fields=["priority", "updated_at"])
            _event(ticket, staff_user, f"Priority set to {SupportTicket.Priority(priority).label}.", staff_only=True)
            record("support.priority_changed", actor=staff_user, subject_user=ticket.candidate, target=ticket, priority=priority)
        if assigned_to != "unchanged":
            assignee = None
            if assigned_to is not None:
                assignee = StaffSupportService.staff_users().filter(pk=assigned_to).first()
                if assignee is None:
                    raise SupportError("Tickets can only be assigned to staff.")
            if assignee != ticket.assigned_to:
                ticket.assigned_to = assignee
                ticket.save(update_fields=["assigned_to", "updated_at"])
                _event(ticket, staff_user, f"Assigned to {_display(assignee)}." if assignee else "Unassigned.", staff_only=True)
                record("support.assigned", actor=staff_user, subject_user=ticket.candidate, target=ticket,
                       assignee_id=assignee.pk if assignee else None)
        if status:
            StaffSupportService._set_status(staff_user, ticket, status)
        return ticket

    @staticmethod
    def mark_read(ticket: SupportTicket) -> None:
        SupportTicket.objects.filter(pk=ticket.pk).update(staff_last_read_at=timezone.now())
