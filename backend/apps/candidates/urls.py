from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me, name="me"),
    path("profile/", views.profile, name="profile"),
    path("resumes/jobs/<int:job_id>/draft/", views.job_draft, name="resume-job-draft"),
]
