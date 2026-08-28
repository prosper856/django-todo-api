import re
from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.choices import UserTypeChoices, StatusChoices
from apps.base.account_utils import (
    email_validator,
    set_user_otp,
    send_otp_email,
    complete_password_reset,
)
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Basic user profile serializer."""
    class Meta:
        model =User
        fields = ["id", "email", "username",
         "first_name", "last_name", "user_type", "is_active", "is_staff"]
        read_only_fields =["id", "is_active", "is_staff"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Registers new user, enforces password rules, and triggers verification OTP."""
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"}
    )
    confirm_password =serializers.CharField(
        write_only=True,
        style={"input_type": "password"}

    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name","username", "password", "confirm_password"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }
    def validate_email(self, value):
        email = value.lower().strip()

        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")

        return email


    def validate_username(self, value):
        if not value or value.strip() == "":
            return None 
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, data):
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        if password != confirm_password:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})
        if not re.search(r"[a-zA-Z]", password) or not re.search(r"\d", password):
            raise serializers.ValidationError({"password": "Password must contain both letters and digits."})

        # Validate the password using Django's built-in validators
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return data
    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        email = validated_data["email"]
        username = validated_data["username"]
        first_name = validated_data.get("first_name", "")
        last_name = validated_data.get("last_name", "")
        password = validated_data["password"]
        user_type = validated_data.get("user_type", UserTypeChoices.USER)

        user = User.objects.create_user(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_active=False,  # User is inactive until email verification
        
        )
        if hasattr(user, "user_type"):
            user.user_type = user_type
        elif hasattr(user, "user_type"):
            user.user_type = user_type
            user.save()

        # Generate and send OTP for email verification
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "account_verification")

        return user




class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification using OTP."""
    email = serializers.EmailField(write_only=True)
    otp = serializers.CharField(max_length=6, write_only=True)

    def validate_email(self, value):
        return value.lower().strip()

    
class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer with read-only email."""
    class Meta:
        model= User
        fields= ["id", "email", "username", "first_name", "last_name", "user_type", "is_active", "is_staff", "created_at", "updated_at"]
        read_only_fields=["id", "email", "is_active", "is_staff"]




class LoginSerializer(serializers.Serializer):
    """Handles user login and token generation."""
    email = serializers.EmailField(required = False, allow_blank=True)
    username = serializers.CharField(allow_blank = True, required=False)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    

    def validate(self, attrs):
        email = (attrs.get("email") or "").lower().strip()
        username = (attrs.get("username") or "").strip()
        password = attrs .get("password", "")
        


        identifier = email or username
        if not identifier:
            raise serializers.ValidationError("Please provide either an email or username")

        user = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("Account is not active or not verified. Please check your email for verification instructions.")
        attrs["user"] = user
        return attrs
    

class LogoutSerializer(serializers.Serializer):
    """Handles user logout by blacklisting the refresh token."""
    refresh = serializers.CharField(write_only=True)

    def validate(self, data):
        self.token = data.get("refresh")
        return data

    def save(self, **kwargs):
        try:
            # Blacklist the refresh token
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh": "Invalid or expired refresh token."})

class PasswordResetRequestSerializer(serializers.Serializer):
    """Handles password reset requests by sending an OTP to the user's email."""
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()
        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        return email

    def save(self):
        email = self.validated_data["email"]
        user = User.objects.filter(email__iexact=email).filter()
        if user:
           otp = set_user_otp(user)
           send_otp_email(user.id, otp, "password_reset")
        return True

class CompletePasswordResetSerializer(serializers.Serializer):
    """Handles the completion of the password reset process using OTP."""
    email = serializers.EmailField(write_only=True)
    otp = serializers.CharField(max_length=6, write_only=True)
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value):
        email = value.lower().strip()
        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        return email

    def validate(self, data):
        new_password = data.get("new_password")
        confirm_new_password = data.get("confirm_new_password")

        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        if len(new_password) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters long."})
        if not re.search(r"[a-zA-Z]", new_password) or not re.search(r"\d", new_password):
            raise serializers.ValidationError({"new_password": "Password must contain both letters and digits."})

        return data

    def save(self):
        email = self.validated_data["email"]
        otp = self.validated_data["otp"]
        new_password = self.validated_data["new_password"]
        success = complete_password_reset(email, otp, new_password)
        if not success:
            raise serializers.ValidationError({"detail": "Invalid, expired OTP, or reset request failed."})
        
        return True 


class ResendOTPSerializer(serializers.Serializer):
    """Handles resending OTP for account verification or password reset."""
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()
        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        return email
    def save(self):
        email = self.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user:
            if not user.is_active:
                otp = set_user_otp(user)
                send_otp_email(user.id, otp, "account_verification")
            else:
                otp = set_user_otp(user)
                send_otp_email(user.id, otp, "password_reset")
                 # Do not reveal that the email does not exist for security reasons
        return True 


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]

    def validate_username(self, value):
        if not value or value.strip() == "":
            return None
        value = value.strip()

        request= self.context.get("request")
        current_user = request.user if request else None
        query = User.objects.filter(username__iexact=value)
        if current_user and current_user.pk:
           query = query.exclude(pk=current_user.pk)

        if query.exists():
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_first_name(self, value):
        return value.strip()  # Remove leading/trailing whitespace
    def validate_last_name(self, value):
        return value.strip()  # Remove leading/trailing whitespace
    def update(self, instance, validated_data):
        instance.username = validated_data.get("user", instance.username)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()
        return instance



class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        user = self.context.get("request").user
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_new_password = data.get("confirm_new_password")
        if not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Your current password is incorrect."})
        if new_password != confirm_new_password:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        if old_password == new_password:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})
        if len(new_password) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters long."})
        if not re.search(r"[a-zA-Z]", new_password) or not re.search(r"\d", new_password):
            raise serializers.ValidationError({"new_password": "Password must contain both letters and digits."})

        return data

    def save(self, **kwargs):
        user = self.context.get("request").user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        return user



class ChangeEmailSerializer(serializers.Serializer):
    """Serializer for changing user email."""
    new_email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_new_email(self, value):
        new_email = value.lower().strip()
        if not email_validator(new_email):
            raise serializers.ValidationError("Invalid email address format.")
        if User.objects.filter(email=new_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return new_email

    def validate(self, data):
        user = self.context.get("request").user
        password = data.get("password")
        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Your current password is incorrect."})
        return data

    def save(self, **kwargs):
        user = self.context.get("request").user
        new_email = self.validated_data["new_email"]
        user.email = new_email
        user.is_active = False  # Deactivate until email verification
        user.save()
        
        # Generate and send OTP for email verification
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email_change_verification")

        return user   

        
               

    