from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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

        if user.is_staff:
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
        fields = ['email', 'first_name', 'last_name', 'username', 'password', 'password_confirm', 'patronymic']

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
