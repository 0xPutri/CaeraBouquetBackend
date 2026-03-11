from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView

urlpatterns = [
    # Endpoint Registrasi
    path('register/', RegisterView.as_view(), name='register'),

    # Endpoint Login
    path('login/', TokenObtainPairView.as_view(), name='login'),

    # Endpoint Refresh Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]