from django.urls import path

from . import views

urlpatterns = [
    path("resumes/", views.upload_resume, name="resume-upload"),
    path("resumes/jobs/latest/", views.latest_job, name="resume-job-latest"),
    path("resumes/jobs/<int:job_id>/", views.job_detail, name="resume-job-detail"),
    path("resumes/jobs/<int:job_id>/retry/", views.retry_job, name="resume-job-retry"),
]
