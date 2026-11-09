from django.urls import path

from . import views

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="auth-register"),
    path("verify-email", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification", views.ResendVerificationView.as_view(), name="auth-resend"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("refresh", views.RefreshView.as_view(), name="auth-refresh"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("password-reset", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("me/export", views.MeExportView.as_view(), name="auth-me-export"),
]
