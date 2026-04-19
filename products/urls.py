from django.urls import path, include

from .views import ProductListView, ProductDetailView, CategoryListView, CategoryDetailView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('category/', CategoryListView.as_view(), name='category-list'),
    path('category/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('<int:pk>/', include("reviews.urls")),
]
