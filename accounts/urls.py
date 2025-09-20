from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from accounts.views import RegisterAPIView, MyTokenObtainPairView, LoginAPIView, LogoutAPIView


urlpatterns = [
    # Это корневой URL. Все запросы, отправленные на корневой URL вашего API, будут перенаправлены в RegisterAPIView
    path('', RegisterAPIView.as_view(), name='registration'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    # Этот URL предназначен для получения пары JWT-токенов (access token и refresh token)
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Этот URL предназначен для обновления токена доступа (access token) с помощью refresh token.
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Этот URL предназначен для проверки действительности токена доступа (access token).
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]