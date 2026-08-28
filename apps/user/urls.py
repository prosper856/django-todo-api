from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.user.views import (
    UserViewSet,
    LoginView,
    LogoutView,
    EmailVerificationView,
    ResendOTPView,
    ChangePasswordView,
    ChangeEmailView,
    PasswordResetRequestView,
    CompletePasswordResetView,
)

app_name = "user"

router = DefaultRouter()
router.register(r"", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify/email/", EmailVerificationView.as_view(), name="email_verification"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend_otp"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("change-email/", ChangeEmailView.as_view(), name="change_email"),
    path("reset-password/request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("reset-password/confirm/", CompletePasswordResetView.as_view(), name="password_reset_complete"),
    path("", include(router.urls)),

]