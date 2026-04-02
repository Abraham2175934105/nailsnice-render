from rest_framework.permissions import BasePermission, SAFE_METHODS

from .auth import is_admin_user


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin_user(request.user)


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)
