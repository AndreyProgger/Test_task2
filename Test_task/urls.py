"""
URL configuration for Test_task project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path('admin2/', admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    # Этот путь предоставляет доступ к сырой спецификации OpenAPI вашего API в формате JSON
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    #  Этот путь предоставляет доступ к интерактивному интерфейсу Swagger UI
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/products/", include("products.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/admin2/", include("admin2.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += debug_toolbar_urls()
