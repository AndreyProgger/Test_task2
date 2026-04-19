from django.urls import path

from .views import CartByUserListView, CartClearView, CartItemView

urlpatterns = [
    path('', CartByUserListView.as_view(), name='cart'),
    path('clear/', CartClearView.as_view(), name='cart-clear'),
    path('<int:pk>/', CartItemView.as_view(), name='cart-item'),
]
