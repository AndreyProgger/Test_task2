from django.urls import path

from .views import OrderByUserListView, OrderDetailView

urlpatterns = [
    path('', OrderByUserListView.as_view(), name='order-list'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]
