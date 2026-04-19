from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Кастомное разрешение, проверяющее является ли пользователь владельцем конкретного объекта.
    Поддерживает:
    - Прямые модели с полем owner
    - Промежуточные модели (FavoriteItem, OrderItem, CartItem)
    - Связанные объекты
    - Администраторов (role='admin', is_superuser, is_staff) — всегда разрешено
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Администратор всегда имеет доступ к любому объекту
        if self._is_admin_user(request.user):
            return True

        # Прямая проверка для Product
        if hasattr(obj, 'seller'):
            return obj.seller == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        # Остальная логика для промежуточных моделей
        owner = self._get_owner_for_model(obj)
        if owner is None:
            return False
        if hasattr(owner, 'id'):
            return owner.id == request.user.id
        return owner == request.user.id

    def _is_admin_user(self, user):
        """
        Проверяет, является ли пользователь администратором.
        Учитывает различные возможные атрибуты модели пользователя.
        """
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        # Кастомные поля
        if hasattr(user, 'role') and getattr(user, 'role') == 'admin':
            return True
        if hasattr(user, 'is_admin') and getattr(user, 'is_admin') is True:
            return True

        return False

    def _get_owner_for_model(self, obj):
        """
        Определяет владельца объекта на основе его типа.
        """
        model_name = obj.__class__.__name__

        # Обработка промежуточных моделей
        if model_name == 'FavoriteItem':
            return self._get_owner_from_favorite_item(obj)
        elif model_name == 'OrderItem':
            return self._get_owner_from_order_item(obj)
        elif model_name == 'CartItem':
            return self._get_owner_from_cart_item(obj)

        # Обработка прямых моделей через свойство owner
        if hasattr(obj, 'owner'):
            return obj.owner

        # Fallback: поиск стандартных полей
        return self._find_owner_fallback(obj)

    def _get_owner_from_favorite_item(self, obj):
        """
        Получает владельца для элемента избранного.
        FavoriteItem -> Favorite -> User
        """
        try:
            if hasattr(obj, 'favorite') and obj.favorite:
                if hasattr(obj.favorite, 'user'):
                    return obj.favorite.user
                elif hasattr(obj.favorite, 'owner'):
                    return obj.favorite.owner
        except (AttributeError, TypeError):
            pass
        return None

    def _get_owner_from_order_item(self, obj):
        """
        Получает владельца для элемента заказа.
        OrderItem -> Order -> User
        """
        try:
            if hasattr(obj, 'order') and obj.order:
                if hasattr(obj.order, 'user'):
                    return obj.order.user
                elif hasattr(obj.order, 'owner'):
                    return obj.order.owner
        except (AttributeError, TypeError):
            pass
        return None

    def _get_owner_from_cart_item(self, obj):
        """
        Получает владельца для элемента корзины.
        CartItem -> Cart -> User
        """
        try:
            if hasattr(obj, 'cart') and obj.cart:
                if hasattr(obj.cart, 'user'):
                    return obj.cart.user
                elif hasattr(obj.cart, 'owner'):
                    return obj.cart.owner
        except (AttributeError, TypeError):
            pass
        return None

    def _find_owner_fallback(self, obj):
        """
        Поиск владельца по стандартным полям.
        """
        # Пробуем найти поле пользователя напрямую
        possible_fields = ['user', 'owner', 'seller', 'author', 'created_by']

        for field_name in possible_fields:
            value = getattr(obj, field_name, None)
            if value is not None:
                return value

        # Пробуем найти связанный объект и получить его владельца
        related_fields = ['cart', 'order', 'favorite']

        for field_name in related_fields:
            related_obj = getattr(obj, field_name, None)
            if related_obj:
                for user_field in ['user', 'owner']:
                    if hasattr(related_obj, user_field):
                        return getattr(related_obj, user_field)

        return None


class IsAdmin(permissions.BasePermission):
    """Кастомное разрешение проверяющее, является ли пользователь администратором"""

    def has_permission(self, request, view):
        # Проверяем, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return False

        # Проверяем, что пользователь имеет права администратора
        return request.user.is_staff or getattr(request.user, 'role', '') == 'admin'

    def has_object_permission(self, request, view, obj):
        # Для операций с объектами тоже проверяем права админа
        return request.user.is_staff or getattr(request.user, 'role', '') == 'admin'


class IsSeller(permissions.BasePermission):
    """ Кастомное разрешение проверяющее, является ли пользователь продавцом """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return getattr(request.user, 'role', '') == 'seller'

    def has_object_permission(self, request, view, obj):
        return getattr(request.user, 'role', '') == 'seller'
