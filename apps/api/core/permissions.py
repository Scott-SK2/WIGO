from rest_framework.permissions import BasePermission


class IsModerator(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_moderator or u.is_superuser))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


class IsCatalogEditor(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and (u.is_catalog_editor or u.is_moderator or u.is_superuser)
        )


class HasVerifiedEmail(BasePermission):
    """RG-02 : e-mail vérifié obligatoire avant publication."""

    message = "Vérifiez votre adresse e-mail avant de publier."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.email_verified_at is not None)
