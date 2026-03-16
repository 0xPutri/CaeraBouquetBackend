from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/', include('users.urls')), # /api/auth/* & /api/users/*
    path('api/', include('products.urls')), # /api/categories/ & /api/products/
    path('api/', include('orders.urls')), # /api/orders/
]