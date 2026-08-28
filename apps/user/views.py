from rest_framework.views import APIView
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.base.account_utils import send_otp_email, set_user_otp
from core.utils import send_welcome_email
from apps.base.permissions import IsAdminOrOwner

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
    ChangePasswordSerializer,
    ChangeEmailSerializer,
)

User = get_user_model()

@extend_schema(tags=["User"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "retrieve":
            return UserDetailSerializer
        return UserSerializer
    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrOwner()]

    def perform_create(self, serializer):
        user = serializer.save()
        send_welcome_email(user.email, user.username, user.first_name)

@ extend_schema(tags=["Authentication"])
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful",
                response=UserSerializer,
            ),
            400: OpenApiResponse(
                description="Invalid credentials",
            ),
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
            200: OpenApiResponse(
                description="Logout successful",
            ),
            400: OpenApiResponse(
                description="Invalid token",
            ),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"message": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Authentication"])
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(
                description="Email verification successful",
            ),
            400: OpenApiResponse(
                description="Invalid OTP or email",
            ),
        },
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "User does not exist."}, status=status.HTTP_400_NOT_FOUND)
        
        if user.otp != otp:
            return Response({"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.otp_verified = True
        user.otp = None  # Clear the OTP after successful verification
        user.save()
        return Response({"message": "Email verification successful."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="A new OTP has been sent to your email.",
            ),
            400: OpenApiResponse(
                description="Invalid email",
            ),
        },
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)



@extend_schema(tags=["Authentication"])
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully",
            ),
            400: OpenApiResponse(
                description="Invalid data",
            ),
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
            200: OpenApiResponse(
                description="Email changed successfully",
            ),
            400: OpenApiResponse(
                description="Invalid data",
            ),
        },
    )
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": f"Verification code sent to {serializer.validated_data["new_email"]}."}, status=status.HTTP_200_OK)

@extend_schema(tags=["Authentication"])
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset email sent successfully",
            ),
            400: OpenApiResponse(
                description="Invalid email",
            ),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({"message": "If an account with this email exists, an OTP has been sent to the email address provided."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class CompletePasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CompletePasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successful",
            ),
            400: OpenApiResponse(
                description="Invalid OTP or email",
            ),
        },
    )
    def post(self, request):
        serializer = CompletePasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK) 
