from django.urls import path
from .views import LoginView, RegisterView, TokenRefreshDocsView, UserProfileView

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshDocsView.as_view(), name='token_refresh'),
    
    # User Endpoints
    path('users/profile/', UserProfileView.as_view(), name='user_profile'),
]
