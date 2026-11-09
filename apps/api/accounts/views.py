from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.audit import log_action
from core.throttles import AuthThrottle

from . import serializers, services
from .models import User

UserModel = get_user_model()


class RegisterView(generics.CreateAPIView):
    """AUTH-01 : inscription par e-mail, envoi du lien de vérification (RG-02)."""

    serializer_class = serializers.RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def perform_create(self, serializer):
        user = serializer.save()
        services.send_verification_email(user)
        log_action(user, "account.register", user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": "Compte créé. Vérifiez votre boîte e-mail."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """AUTH-02 : consommation du jeton de vérification."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=serializers.TokenSerializer, responses={200: serializers.MeSerializer})
    def post(self, request):
        s = serializers.TokenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = services.verify_email(s.validated_data["token"])
        if user is None:
            return Response(
                {"detail": "Lien invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST
            )
        log_action(user, "account.email_verified", user)
        return Response(serializers.MeSerializer(user).data)


class ResendVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=None, responses={202: None})
    def post(self, request):
        if not request.user.is_email_verified:
            services.send_verification_email(request.user)
        return Response(status=status.HTTP_202_ACCEPTED)


class LoginView(TokenObtainPairView):
    """AUTH-03 : paire de jetons (access 15 min, refresh 14 j avec rotation)."""

    throttle_classes = [AuthThrottle]


class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    """Révocation de la session : le refresh token est mis sur liste noire."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request={"application/json": {"type": "object"}}, responses={204: None})
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """AUTH-04 : demande de réinitialisation (réponse identique que l'e-mail existe ou non)."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=serializers.EmailSerializer, responses={202: None})
    def post(self, request):
        s = serializers.EmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(email=s.validated_data["email"].lower()).first()
        if user and user.is_active:
            services.send_password_reset_email(user)
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=serializers.PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        from .models import AccountToken, TokenKind

        s = serializers.PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = AccountToken.consume(s.validated_data["token"], TokenKind.PASSWORD_RESET)
        if user is None:
            return Response(
                {"detail": "Lien invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(s.validated_data["password"])
        user.save(update_fields=["password"])
        log_action(user, "account.password_reset", user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateDestroyAPIView):
    """AUTH-05 / AUTH-06 : profil, suppression du compte (anonymisation)."""

    serializer_class = serializers.MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        log_action(instance, "account.delete", instance)
        services.anonymize_user(instance)


class MePreferencesView(generics.RetrieveUpdateAPIView):
    """SCR-13 : quartiers, envies, interrupteurs de notification."""

    serializer_class = serializers.PreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class MeExportView(APIView):
    """AUTH-06 / RG-18 : export des données personnelles (JSON)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request):
        log_action(request.user, "account.export", request.user)
        return Response(services.export_user_data(request.user))
