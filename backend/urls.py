from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/', include('users.urls')), # /api/auth/* & /api/users/*
    path('api/', include('products.urls')), # /api/categories/ & /api/products/
    path('api/', include('orders.urls')), # /api/orders/
    path('api/health/', HealthCheckView.as_view(), name='health-check'),

    # Endpoint Dokumentasi OpenAPI/Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'), # Download YAML/JSON
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'), # Tampilan UI
]