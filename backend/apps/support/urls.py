from django.urls import path

from . import views

urlpatterns = [
    path("support/tickets/", views.tickets, name="support-tickets"),
    path("support/tickets/<str:number>/", views.ticket_detail, name="support-ticket"),
    path("support/tickets/<str:number>/messages/", views.ticket_reply, name="support-ticket-reply"),
    path("support/tickets/<str:number>/close/", views.ticket_close, name="support-ticket-close"),
    path("support/attachments/<int:attachment_id>/", views.attachment, name="support-attachment"),
    path("admin/support/tickets/", views.staff_tickets, name="staff-support-tickets"),
    path("admin/support/tickets/<str:number>/", views.staff_ticket, name="staff-support-ticket"),
    path("admin/support/tickets/<str:number>/messages/", views.staff_reply, name="staff-support-reply"),
    path("admin/support/staff/", views.staff_users, name="staff-support-staff"),
]
