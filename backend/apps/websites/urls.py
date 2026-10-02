from django.urls import path

from . import public_views, views

urlpatterns = [
    path("website/", views.website, name="website"),
    path("website/catalog/", views.catalog, name="website-catalog"),
    path("website/slug-available/", views.slug_available, name="website-slug-available"),
    path("website/bio/draft/", views.draft_bio, name="website-bio-draft"),
    path("website/preview/", views.preview, name="website-preview"),
    path("website/render/preview/<str:token>/", views.render_preview, name="website-render-preview"),
    path("website/publish/", views.publish, name="website-publish"),
    path("website/unpublish/", views.unpublish, name="website-unpublish"),
    path("public/sites/<str:slug>/", public_views.public_site, name="public-site"),
    path("public/sites/<str:slug>/chat/", public_views.site_chat, name="public-site-chat"),
    path("public/sites/<str:slug>/chat/<str:session_id>/", public_views.site_chat_transcript, name="public-site-chat-transcript"),
    path("public/sites/<str:slug>/match/", public_views.site_match, name="public-site-match"),
    path("public/sites/<str:slug>/match/<str:match_id>/", public_views.site_match_detail, name="public-site-match-detail"),
]
