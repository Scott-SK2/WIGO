from django.urls import path

from . import views

urlpatterns = [
    path("reports", views.ReportCreateView.as_view(), name="report-create"),
    path("admin/moderation", views.ModerationQueueView.as_view(), name="admin-moderation"),
    path(
        "admin/moderation/reasons", views.ReasonCodesView.as_view(), name="admin-moderation-reasons"
    ),
    path("admin/reports", views.ReportListView.as_view(), name="admin-reports"),
    path(
        "admin/reports/<uuid:pk>/decide",
        views.ReportDecisionView.as_view(),
        name="admin-report-decide",
    ),
    path("admin/claims", views.ClaimListView.as_view(), name="admin-claims"),
    path(
        "admin/claims/<uuid:pk>/decide",
        views.ClaimDecisionView.as_view(),
        name="admin-claim-decide",
    ),
    path("admin/audit", views.AuditLogView.as_view(), name="admin-audit"),
]
