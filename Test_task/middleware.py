from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class JWTAutoRefreshMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        if (hasattr(request, 'user') and
                request.user.is_authenticated and
                hasattr(request, 'auth')):

            # Проверяем, нужно ли обновить токен
            try:
                refresh = RefreshToken(request.COOKIES.get('refresh_token'))
                new_access_token = str(refresh.access_token)

                # Устанавливаем новый access token в cookie
                response.set_cookie(
                    key='access_token',
                    value=new_access_token,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    max_age=3600
                )
            except (TokenError, AttributeError):
                pass

        return response
