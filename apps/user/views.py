from rest_framework.views import APIView
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.base.account_utils import send_otp_email, set_user_otp
from apps.user.serializers import UserCreateSerializer, UserDetialSerializer, UserSerializer, LoginSerializer, ChangePasswordSerializer, OTPVerificationSerializer, PasswordResetRequestSerializer, CompletePasswordResetSerializer, UserUpadteSerializer,UserDetialSerializer


User = get_user_model()


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.exclude(status='DELETED')
    permission_classes = [IsAuthenticated, permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSerializer
        elif self.action == 'retrieve':
            return UserDetialSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'admin_users':  # Add this condition
            return UserSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
           return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
             return [IsAuthenticated()]
        else:
            return [IsAuthenticated(), IsAdminUser]
        return [perm() for perm in permission_classes]


    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: UserDetialSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Create a new user",
        description="Create a new user with email, first name, last name, and password."
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


    @extend_schema(
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="List Users",
        description="Retrieve a list of all users. only admin users can access this endpoint."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @extend_schema(
        responses={
            200: UserDetialSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Retrieve a user",
        description="Retrieve details of a specific user by ID."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    

    @extend_schema(
        request=UserUpadteSerializer,
        responses={
            200: UserDetialSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Update a user",
        description="Update details of a specific user by ID."
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Partially Update a user",
        description="Partially Update details of a specific user by ID."
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: UserSerializer(many=True),  # Changed to many=True for list response
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Lists of Admin Users",
        description="Retrieve a list of all admin users."
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def admin_users(self, request, *args, **kwargs):
        # Filter for admin users only
        admin_users = self.get_queryset().filter(is_staff=True)  # or however you identify admin users

        # Learn Pipe Queries 
        # Use pagination if you have it enabled
        page = self.paginate_queryset(admin_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # If no pagination, return all admin users
        serializer = self.get_serializer(admin_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# list, retrieve, create, update, partial_update, destroy

@extend_schema(tags=["Authentication"])
class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="User Login",
        description="Authenticate a user with email and password."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = serializer.validated_data['tokens']
        return Response({
            "user": UserDetialSerializer(user).data,
            "tokens": {
                "access": tokens['access'],
                "refresh": tokens['refresh'],
            }
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="Logout successful"),
            401: OpenApiResponse(description="Unauthorized"),
        },
        summary="User Logout",
        description="Logout a user by invalidating their refresh token."
    )
    def post(self, request, *args, **kwargs):
        refresh = request.data.get('refresh')
        if refresh:
            RefreshToken(refresh).blacklist()
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK
        )


@extend_schema(tags=["Authentication"])
class ChangePasswordView(generics.GenericAPIView):
    serializer_class =ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
        },
        summary="Change User Password",
        description="Change the password of the authenticated user."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        serializer.save(user=user)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

@extend_schema(tags=["Verfication"])
class EmailVerificationView(generics.GenericAPIView):
    permission_classes = [AllowAny]  # Changed from IsAuthenticated to AllowAny
    serializer_class = OTPVerificationSerializer
    
    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="OTP Sent successfully"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Send OTP",
        description="Send an OTP to the user's email for verification purposes."
    )
    def get(self, request, *args, **kwargs):
        # You'll need to modify this to get the user differently since request.user won't be available
        # Option 1: Get user by email from query params
        email = request.query_params.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email verification")
        return Response({"detail": "OTP sent to your email."}, status=status.HTTP_200_OK)
    

    @extend_schema(
        request=OTPVerificationSerializer,
        responses={
            200: OpenApiResponse(description="OTP Verified successfully"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Verify OTP",
        description="Verify the OTP sent to the user's email."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the user from the serializer's validated data
        user = serializer.validated_data['user']
        user.otp = None
        user.otp_created_at = None
        user.otp_verified = True  # Mark as verified
        user.is_active = True
        user.save(update_fields=['otp', 'otp_created_at', 'otp_verified', 'is_active'])
        
        return Response({"detail": "OTP verified successfully."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Password Reset"])
class PasswordRequestResetView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(response=None),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Initiate Password Reset",
        description="Send an OTP to the user's email for password reset."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ChangePasswordSerializer
    
    @extend_schema(
        request=CompletePasswordResetSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Complete Password Reset",
        description="Complete the password reset process by verifying OTP and setting a new password."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)