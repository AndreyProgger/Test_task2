import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework import status

from orders.models import Order, OrderItem
from .models import Review

pytestmark = pytest.mark.django_db


class TestReviewModel:
    def test_create_review(self, user, product, order2):
        review = Review.objects.create(
            product=product,
            user=user,
            rating=4,
            text='Good product'
        )
        assert review.rating == 4
        assert review.text == 'Good product'
        assert review.is_published is True
        assert str(review) == f'Отзыв от {user} на {product} (оценка 4)'

    def test_review_unique_together(self, user, product, order2):
        Review.objects.create(product=product, user=user, rating=5, text='First')
        with pytest.raises(Exception):
            Review.objects.create(product=product, user=user, rating=4, text='Duplicate')

    def test_review_cannot_review_own_product(self, seller_user, product, order2):
        # order принадлежит seller_user? но для проверки валидации создадим отзыв продавца на свой товар
        with pytest.raises(ValidationError, match='Нельзя оставить отзыв на свой товар'):
            review = Review(product=product, user=seller_user, rating=5, text='My own product')
            review.full_clean()  # вызывает clean() и ValidationError

    def test_review_requires_completed_order(self, user, product):
        with pytest.raises(ValidationError,
                           match='Нельзя оставить отзыв на товар, так как нет завершенных заказов с этим товаром.'):
            review = Review(product=product, user=user, rating=5, text='No order')
            review.full_clean()

    def test_review_rating_range(self, user, product, order2):
        # rating 0 - недопустимо
        with pytest.raises(ValidationError):
            review = Review(product=product, user=user, rating=0, text='Zero')
            review.full_clean()
        # rating 6 - недопустимо
        with pytest.raises(ValidationError):
            review = Review(product=product, user=user, rating=6, text='Six')
            review.full_clean()


class TestReviewsAPI:

    def test_list_reviews_unauthenticated(self, api_client, product, review):
        url = reverse('reviews', args=[product.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['text'] == review.text

    def test_list_reviews_authenticated(self, auth_client, product, review):
        client, _ = auth_client
        url = reverse('reviews', args=[product.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_create_review_success(self, auth_client, product):
        client, user = auth_client
        order = Order.objects.create(user=user, status='completed')
        OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)

        url = reverse('reviews', args=[product.id])
        data = {'rating': 5, 'text': 'Excellent!'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Review.objects.filter(product=product, user=user).exists()
        review = Review.objects.get(product=product, user=user)
        assert review.rating == 5
        assert review.text == 'Excellent!'

    def test_create_review_unauthenticated(self, api_client, product):
        url = reverse('reviews', args=[product.id])
        data = {'rating': 5, 'text': 'Nice'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_review_on_own_product(self, seller_auth_client, product):
        client, seller = seller_auth_client
        url = reverse('reviews', args=[product.id])
        data = {'rating': 5, 'text': 'My own product review'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'Нельзя оставить отзыв на свой товар' in response.data['error']

    def test_create_review_without_completed_order(self, auth_client, product):
        client, user = auth_client
        url = reverse('reviews', args=[product.id])
        data = {'rating': 5, 'text': 'No order'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'нет завершенных заказов' in response.data['error'].lower()

    def test_create_review_invalid_rating(self, auth_client, product):
        client, user = auth_client
        order = Order.objects.create(user=user, status='completed')
        OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)

        url = reverse('reviews', args=[product.id])
        data = {'rating': 10, 'text': 'Too high'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # формат ошибки может быть {'details': {'rating': ...}}
        assert 'rating' in response.data.get('details', {})

    def test_create_duplicate_review(self, auth_client, product):
        client, user = auth_client
        order = Order.objects.create(user=user, status='completed')
        OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
        Review.objects.create(product=product, user=user, rating=5, text='First')
        url = reverse('reviews', args=[product.id])
        data = {'rating': 3, 'text': 'Duplicate'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

