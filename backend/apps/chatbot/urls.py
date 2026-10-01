from django.urls import path

from . import views

urlpatterns = [
    path("public/p/<str:token>/chat/", views.ask, name="public-chat"),
    path("public/p/<str:token>/chat/<str:session_id>/", views.transcript, name="public-chat-transcript"),
    path("employer-profile/chats/", views.my_sessions, name="employer-chats"),
    path("employer-profile/chats/<str:session_id>/", views.my_session_detail, name="employer-chat-detail"),
]
