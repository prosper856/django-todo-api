from rest_framework import permissions

class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access certain views.
    """


    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        is_admin = request.user.is_staff or getattr(request.user, "user_type", None) =="ADMIN"
        if is_admin:
            return True
        return obj == request.user or getattr(obj,"user", None) == request.user


class IsUnverified(permissions.BasePermission):
    """
    Custom permission to only allow unverified users to access certain views.
    """

    def has_permission(self, request, view):
        return bool(
        request.user
        and request.user.is_authenticated
        and not getattr(request.user, "otp_verified", False )
        )