import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from accounts.serializers import CreateUserSerializer, MyTokenObtainPairSerializer, LoginSerializer, \
    ChangePasswordSerializer, UserProfileSerializer, UserProfileUpdateSerializer
from common.permissions import IsOwner

User = get_user_model()

tags = ["auth"]

logger = logging.getLogger(__name__)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # Устанавливаем cookies с токенами
        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            # Устанавливаем cookies
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,  # True для HTTPS
                samesite='Lax',
                max_age=3600  # 1 час
            )

            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=7 * 24 * 3600  # 1 неделя
            )

        return response


class RegisterAPIView(APIView):
    serializer_class = CreateUserSerializer
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Registration",
        description="""
                    This endpoint allows to registration.
                """,
        tags=tags,
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Генерируем токены для нового пользователя
            refresh = RefreshToken.for_user(user)

            # Создаем response с cookies
            response_data = {
                'message': 'success',
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'patronymic': user.patronymic,
                    'role': user.role,
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }

            response = Response({'message': "success"}, status=201)

            # Устанавливаем cookies
            response.set_cookie(
                key='access_token',
                value=str(refresh.access_token),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=3600
            )

            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=7 * 24 * 3600
            )
            logger.info(f'Пользователь: {user.username} успешно зарегистрирован')
            return response
        # Я поставил уровень debug чтобы не засорять файл подобными ошибками
        logger.debug(f'Ошибка валидации при регистрации пользователя с данными: {request.data}')
        return Response(serializer.errors, status=400)


class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Login",
        description="""
                        This endpoint allows to log in system.
                    """,
        tags=tags,
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Проверяем активность пользователя
            user = serializer.user
            if not user.is_active:
                logger.warning(f'Пользователь: {user.username} не смог войти в свой аккаунт, так как он не активен')
                return Response(
                    {"message": "Аккаунт неактивен. Обратитесь к администратору."},
                    status=404
                )
            logger.info(f'Пользователь: {user.username} успешно вошел в свой аккаунт')
            return Response(serializer.validated_data, status=200)
        logger.debug(f'Ошибка валидации при входе пользователя с данными: {request.data}')
        return Response(serializer.errors, status=400)


class LogoutAPIView(APIView):

    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Logout",
        description="""
                            This endpoint allows to log out from system.
                        """,
        tags=tags,
    )
    def post(self, request):
        response = Response({'message': 'Successfully logged out'})

        # Удаляем cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        # Также можно добавить blacklist для refresh token
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        return response


class UserProfileView(APIView):
    """
    Просмотр профиля текущего пользователя.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        summary="Получение профиля",
        description="Возвращает данные текущего пользователя и его расширенный профиль.",
        tags=["profile"],
    )
    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user)
        logger.info(f'Пользователь {request.user.email} запросил свой профиль')
        return Response(serializer.data)

    def get_object(self):
        return self.request.user


class UserProfileUpdateView(APIView):
    """
    Обновление профиля текущего пользователя (User + Profile).
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        summary="Обновление профиля",
        description="Обновляет данные пользователя и его расширенный профиль.",
        tags=["profile"],
    )
    def patch(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            user = serializer.save()
            logger.info(f'Пользователь {user.email} обновил свой профиль')
            profile_serializer = UserProfileSerializer(user, context={'request': request})
            return Response({
                'message': 'Профиль успешно обновлен',
                'user': profile_serializer.data
            }, status=200)

        logger.debug(f'Ошибка обновления профиля: {serializer.errors}')
        return Response(serializer.errors, status=400)

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    Смена пароля текущего пользователя.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        summary="Смена пароля",
        description="Изменяет пароль пользователя и инвалидирует все его токены.",
        tags=["profile"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            logger.info(f'Пользователь {user.email} сменил пароль')

            tokens = OutstandingToken.objects.filter(user_id=user.id)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

            response = Response({
                'message': 'Пароль успешно изменен. Пожалуйста, войдите снова.'
            }, status=200)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response

        logger.debug(f'Ошибка смены пароля: {serializer.errors}')
        return Response(serializer.errors, status=400)

    def get_object(self):
        return self.request.user

