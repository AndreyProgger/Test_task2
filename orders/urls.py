from django.urls import path

from .views import OrderByUserListView, OrderDetailView, StatusUpdateView

urlpatterns = [
    path('', OrderByUserListView.as_view(), name='order-list'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/status/', StatusUpdateView.as_view(), name='order_status-update'),
]
