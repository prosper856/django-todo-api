import logging
import secrets

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.permissions import IsAdminOrOwner
from apps.base.account_utils import send_otp_email  # Ensure send_otp_email is imported
from apps.user.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    LoginSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    PasswordResetRequestSerializer,
    CompletePasswordResetSerializer,
    ResendOTPSerializer,
    UserUpdateSerializer,
    ChangeEmailSerializer,
)
from core.utils import send_welcome_email

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(tags=["User"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_queryset(self):
        # Avoid touching request.user during OpenAPI schema generation
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        user = self.request.user
        # Admins see everyone; regular users only see themselves
        if user.is_authenticated and user.is_staff:
            return User.objects.all()
        if user.is_authenticated:
            return User.objects.filter(pk=user.pk)
        return User.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "retrieve":
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrOwner()]

    def perform_create(self, serializer):
        # 1. Save user with is_active=False
        user = serializer.save(is_active=False)

        # 2. Generate a 6-digit OTP code if not already created in serializer
        otp = f"{secrets.randbelow(1000000):06d}"
        user.otp = otp
        user.save(update_fields=["otp"])

        # 3. Send the OTP email immediately upon registration
        try:
            send_otp_email(user.id, otp, "account_verification")
        except Exception:
            logger.exception("Failed to send signup OTP email for user id=%s", user.id)


@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful", response=UserSerializer),
            400: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserDetailSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logout successful"),
            400: OpenApiResponse(description="Invalid token"),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # blacklists the token; raises a 400 if invalid/expired
        return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Email verification successful"),
            400: OpenApiResponse(description="Invalid OTP or email"),
        },
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        user = User.objects.filter(email__iexact=email).first()

        # Same generic error for unknown email / wrong OTP so emails can't be enumerated
        stored_otp = getattr(user, "otp", None) if user else None
        if not user or not stored_otp or not secrets.compare_digest(str(stored_otp), str(otp)):
            return Response(
                {"message": "Invalid OTP or email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first_activation = not getattr(user, "otp_verified", False)

        user.is_active = True
        user.otp_verified = True
        user.otp = None  # clear the OTP after successful verification
        user.save()

        if first_activation:
            try:
                send_welcome_email(user.email, user.username, user.first_name)
            except Exception:
                logger.exception("Welcome email failed for user id=%s", user.id)

        return Response({"message": "Email verification successful."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="A new OTP has been sent to your email."),
            400: OpenApiResponse(description="Invalid email"),
        },
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "If an account with this email exists, a new OTP has been sent."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Invalid data"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangeEmailSerializer,
        responses={
            200: OpenApiResponse(description="Verification code sent to the new email"),
            400: OpenApiResponse(description="Invalid data"),
        },
    )
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        new_email = serializer.validated_data["new_email"]
        return Response(
            {"message": f"Verification code sent to {new_email}."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(description="Password reset email sent successfully"),
            400: OpenApiResponse(description="Invalid email"),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "If an account with this email exists, an OTP has been sent to the email address provided."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class CompletePasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CompletePasswordResetSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid OTP or email"),
        },
    )
    def post(self, request):
        serializer = CompletePasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)