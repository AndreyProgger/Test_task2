import pytest
from django.urls import reverse
from rest_framework import status
from django.core.exceptions import ValidationError

from .models import Favorite, FavoriteItem

pytestmark = pytest.mark.django_db


class TestFavoriteModel:
    def test_create_favorite(self, user):
        favorite = Favorite.objects.create(user=user)
        assert favorite.user == user
        assert favorite.favorites.count() == 0

    def test_one_to_one_relation(self, user):
        fav1 = Favorite.objects.create(user=user)
        with pytest.raises(Exception):  # IntegrityError
            Favorite.objects.create(user=user)


class TestFavoriteItemModel:
    def test_create_favorite_item(self, favorite, product):
        item = FavoriteItem.objects.create(
            favorite=favorite,
            product=product,
            exist=True
        )
        assert item.favorite == favorite
        assert item.product == product
        assert item.exist is True

    def test_unique_together(self, favorite, product):
        FavoriteItem.objects.create(favorite=favorite, product=product, exist=True)
        with pytest.raises(Exception):  # IntegrityError
            FavoriteItem.objects.create(favorite=favorite, product=product, exist=False)

    def test_clean_prevents_own_product(self, favorite, seller_user, product):
        # favorite принадлежит seller_user? Нет, favorite.user = user, а product.seller = seller_user
        # Чтобы проверить свой товар, создадим favorite для seller_user
        seller_favorite = Favorite.objects.create(user=seller_user)
        item = FavoriteItem(favorite=seller_favorite, product=product, exist=True)
        with pytest.raises(ValidationError) as exc:
            item.full_clean()
        assert 'Нельзя добавить свой товар' in str(exc.value)

    def test_clean_prevents_inactive_product(self, favorite, inactive_product):
        item = FavoriteItem(favorite=favorite, product=inactive_product, exist=True)
        with pytest.raises(ValidationError) as exc:
            item.full_clean()
        assert 'неактивный товар' in str(exc.value)

    def test_clean_prevents_deleted_product(self, favorite, deleted_product):
        item = FavoriteItem(favorite=favorite, product=deleted_product, exist=True)
        with pytest.raises(ValidationError) as exc:
            item.full_clean()
        assert 'удаленный товар' in str(exc.value)

    def test_save_reactivates_existing_item(self, favorite, product):
        item1 = FavoriteItem.objects.create(favorite=favorite, product=product, exist=False)
        assert item1.exist is False

        item2, created = FavoriteItem.objects.update_or_create(
            favorite=favorite,
            product=product,
            defaults={'exist': True}
        )

        item1.refresh_from_db()
        assert item1.exist is True
        assert created is False  # не создан новый объект
        assert FavoriteItem.objects.filter(favorite=favorite, product=product).count() == 1


class TestFavoritesAPI:
    def test_get_favorites_unauthenticated(self, api_client):
        url = reverse('favorites-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_favorites_authenticated(self, auth_client, favorite, favorite_item):
        client, user = auth_client
        url = reverse('favorites-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # API возвращает список (без обёртки results)
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        data = response.data[0]
        assert len(data['items']) == 1
        assert data['items'][0]['product_name'] == favorite_item.product.name

    def test_add_product_to_favorites_success(self, auth_client, product):
        client, user = auth_client
        url = reverse('favorites-list')
        data = {'product_id': product.id}   # ключ product_id
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        favorite = Favorite.objects.get(user=user)
        assert favorite.favorites.filter(id=product.id).exists()
        item = FavoriteItem.objects.get(favorite=favorite, product=product)
        assert item.exist is True

    def test_add_product_already_in_favorites(self, auth_client, favorite_item):
        client, user = auth_client
        product = favorite_item.product
        url = reverse('favorites-list')
        data = {'product_id': product.id}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'already in favorites' in response.data['error'].lower()

    def test_add_own_product_to_favorites(self, seller_auth_client, product):
        client, seller = seller_auth_client
        url = reverse('favorites-list')
        data = {'product_id': product.id}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'You can add own product' in response.data['error']

    def test_add_product_without_auth(self, api_client, product):
        url = reverse('favorites-list')
        data = {'product_id': product.id}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_invalid_product(self, auth_client):
        client, _ = auth_client
        url = reverse('favorites-list')
        data = {'product_id': 99999}
        response = client.post(url, data)
        # get_product возвращает 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_product_missing_id(self, auth_client):
        client, _ = auth_client
        url = reverse('favorites-list')
        data = {}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Сериализатор требует product_id
        assert 'product_id' in response.data

    def test_delete_product_from_favorites_success(self, auth_client, favorite_item):
        client, user = auth_client
        product = favorite_item.product
        url = reverse('favorite-detail', args=[product.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FavoriteItem.objects.filter(favorite__user=user, product=product).exists()

    def test_delete_product_not_in_favorites(self, auth_client, product):
        client, user = auth_client
        url = reverse('favorite-detail', args=[product.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_product_unauthenticated(self, api_client, product):
        url = reverse('favorite-detail', args=[product.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


