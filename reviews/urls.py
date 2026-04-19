from django.urls import path

from .views import ReviewsView

urlpatterns = [
    path('reviews/', ReviewsView.as_view(), name='reviews'),
]
