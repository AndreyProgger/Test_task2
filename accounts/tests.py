import pytest
from django.contrib.auth.hashers import check_password
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from accounts.models import Profile, User


@pytest.mark.django_db
class TestProfileModel:
    """Тестирование модели Profile и связанных сигналов."""

    def test_profile_auto_created_on_user_creation(self, user):
        """При создании User автоматически создаётся Profile."""
        assert hasattr(user, 'profile')
        assert isinstance(user.profile, Profile)
        assert user.profile.user == user

    def test_profile_deleted_with_user(self, user):
        """При удалении User каскадно удаляется Profile."""
        profile_id = user.profile.id
        user.delete()
        assert not Profile.objects.filter(id=profile_id).exists()

    def test_profile_str_method(self, user):
        """__str__ профиля возвращает корректную строку."""
        assert str(user.profile) == f"Профиль пользователя {user.email}"

    def test_user_full_name_with_patronymic(self, user):
        """Свойство full_name включает отчество, если оно задано в профиле."""
        user.first_name = "Иван"
        user.last_name = "Иванов"
        user.patronymic = "Иванович"
        user.save()
        user.profile.patronymic = "Иванович"
        user.profile.save()
        assert user.full_name == "Иван Иванович Иванов"


@pytest.mark.django_db
class TestUserProfileRetrieve:

    def test_get_own_profile_authenticated(self, auth_client):
        """Аутентифицированный пользователь получает свой профиль."""
        client, user = auth_client
        url = reverse('user-profile')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['email'] == user.email
        assert data['username'] == user.username
        assert 'profile' in data
        assert data['profile']['patronymic'] == user.profile.patronymic

    def test_get_profile_unauthenticated(self, api_client):
        """Неаутентифицированный пользователь получает 401."""
        url = reverse('user-profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestChangePassword:

    def test_change_password_success(self, auth_client):
        """Успешная смена пароля."""
        client, user = auth_client
        url = reverse('change-password')
        old_password = 'testpass123'
        new_password = 'NewSecurePass456!'
        payload = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': new_password
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Пароль успешно изменен. Пожалуйста, войдите снова.'

        user.refresh_from_db()
        assert check_password(new_password, user.password)

    def test_change_password_wrong_old_password(self, auth_client):
        """Ошибка при неверном старом пароле."""
        client, user = auth_client
        url = reverse('change-password')
        payload = {
            'old_password': 'wrong_old_pass',
            'new_password': 'NewPass123!',
            'confirm_password': 'NewPass123!'
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'old_password' in response.data
        assert 'Неверный текущий пароль' in str(response.data['old_password'])

    def test_change_password_mismatch_confirmation(self, auth_client):
        """Ошибка при несовпадении нового пароля и подтверждения."""
        client, user = auth_client
        url = reverse('change-password')
        payload = {
            'old_password': 'testpass123',
            'new_password': 'NewPass123!',
            'confirm_password': 'DifferentPass456!'
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirm_password' in response.data or 'non_field_errors' in response.data

    def test_change_password_weak_password(self, auth_client):
        """Ошибка валидации слишком простого пароля."""
        client, user = auth_client
        url = reverse('change-password')
        payload = {
            'old_password': 'testpass123',
            'new_password': '123',
            'confirm_password': '123'
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.data

    def test_change_password_unauthenticated(self, api_client):
        """Неаутентифицированный запрос на смену пароля отклоняется."""
        url = reverse('change-password')
        response = api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

