from django.urls import path

from . import match_views, views

urlpatterns = [
    path("employer-profile/", views.employer_profile, name="employer-profile"),
    path("employer-profile/regenerate-link/", views.regenerate_link, name="employer-profile-regenerate"),
    path("employer-profile/activity/", views.activity, name="employer-profile-activity"),
    path("public/p/<str:token>/", views.public_profile, name="public-profile"),
    path("public/p/<str:token>/match/", match_views.public_match, name="public-match"),
    path("public/p/<str:token>/match/<str:match_id>/", match_views.public_match_detail, name="public-match-detail"),
    path("matches/", match_views.my_matches, name="matches"),
    path("matches/<str:match_id>/", match_views.my_match_detail, name="match-detail"),
]
