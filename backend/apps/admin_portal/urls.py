from django.urls import path

from . import views

urlpatterns = [
    path("admin/overview/", views.overview, name="admin-overview"),
    path("admin/users/", views.users, name="admin-users"),
    path("admin/users/<int:user_id>/", views.user_detail, name="admin-user"),
    path("admin/users/<int:user_id>/actions/", views.user_action, name="admin-user-action"),
    path("admin/payments/", views.payments, name="admin-payments"),
    path("admin/ai-jobs/", views.ai_jobs, name="admin-ai-jobs"),
    path("admin/audit/", views.audit, name="admin-audit"),
    path("admin/templates/", views.templates, name="admin-templates"),
    path("admin/templates/versions/", views.template_versions, name="admin-template-versions"),
    path("admin/templates/versions/<int:number>/restore/", views.template_restore, name="admin-template-restore"),
]
