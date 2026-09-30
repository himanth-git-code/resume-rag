from django.urls import path

from . import views

urlpatterns = [
    path("questions/", views.question_list, name="question-list"),
    path("questions/facets/", views.facets, name="question-facets"),
    path("questions/generate/", views.generate, name="question-generate"),
    path("questions/generations/latest/", views.latest_generation, name="question-generation-latest"),
]
