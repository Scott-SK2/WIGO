from django.urls import path

from . import views

urlpatterns = [
    path("newsletter", views.NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
    path("newsletter/confirm", views.NewsletterConfirmView.as_view(), name="newsletter-confirm"),
    path(
        "newsletter/unsubscribe",
        views.NewsletterUnsubscribeView.as_view(),
        name="newsletter-unsubscribe",
    ),
    path("selection", views.PublicSelectionView.as_view(), name="selection-public"),
    path("admin/selection", views.SelectionView.as_view(), name="admin-selection"),
    path("admin/imports", views.ImportsView.as_view(), name="admin-imports"),
    path("admin/stats", views.AdminStatsView.as_view(), name="admin-stats"),
]
