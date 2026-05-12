from django.urls import path

from .views import LoginView, RegisterView, TokenRefreshDocsView, UserProfileView, VerifyEmailView, PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshDocsView.as_view(), name='token_refresh'),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # User Endpoints
    path('users/profile/', UserProfileView.as_view(), name='user_profile'),
]