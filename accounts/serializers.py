from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import Profile

User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Добавляем пользовательские данные в полезную нагрузку
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['username'] = user.username
        token['role'] = user.role

        if user.is_staff or user.role == 'admin':
            token['group'] = 'admin2'
        else:
            token['group'] = 'user'

        return token


class CreateUserSerializer(serializers.ModelSerializer):
    """ Сериализатор представляющий поля для создания пользователя """
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    patronymic = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password', 'role', 'password_confirm', 'patronymic']

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        # Проверка совпадения паролей
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        # Создаем пользователя в базе данных
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            username=validated_data['username'],
            password=password,
            patronymic=validated_data.get('patronymic'),
            role=validated_data['role'],
        )

        return user


class LoginSerializer(serializers.Serializer):
    """ Сериализатор представляющий поля для входа пользователя в систему """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError('Неверные учётные данные')
        self.user = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Profile."""
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'patronymic', 'avatar', 'bio', 'phone',
            'birth_date', 'avatar_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просмотра полного профиля пользователя.
    Включает данные User и вложенный Profile.
    """
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'full_name', 'is_active', 'date_joined', 'last_login',
            'profile'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_active', 'date_joined', 'last_login'
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления данных пользователя (User + Profile).
    """
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'profile']

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким username уже существует.")
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)

        # Обновляем поля User
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()

        # Обновляем поля Profile
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not check_password(value, user.password):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Пароли не совпадают."
            })
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
