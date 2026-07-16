from django.urls import include, path

from rest_framework.routers import DefaultRouter

from apps.user.views import (
    UserViewSet,
    LoginView,
    LogoutView,
    ChangePasswordView,
    EmailVerificationView,
    PasswordRequestResetView,
    PasswordResetConfirmView,       
)

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')


urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("verify/email/", EmailVerificationView.as_view(), name="email_verification"),
    path("password-reset/request/", PasswordRequestResetView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    
]
