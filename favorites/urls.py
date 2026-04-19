from django.urls import path

from .views import FavoritesByUserListView, FavoriteDetailView

urlpatterns = [
    path('', FavoritesByUserListView.as_view(), name='favorites-list'),
    path('<int:pk>/', FavoriteDetailView.as_view(), name='favorite-detail'),
]
