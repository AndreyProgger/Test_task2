from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """ Кастомное разрешение проверяющие является ли пользователь владельцем конкретного объекта """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdmin(permissions.BasePermission):
    """ Кастомное разрешение проверяющие является ли пользователь администратором """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff