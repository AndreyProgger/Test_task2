from django.urls import path

from .views import AddressByUserListView, AddressDetailView

urlpatterns = [
    path('', AddressByUserListView.as_view(), name='address-list'),
    path('<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
]
