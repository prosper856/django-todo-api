import logging
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.choices import UserTypeChoices
from apps.base.account_utils import (
    email_validator,
    set_user_otp,
    send_otp_email,
    complete_password_reset,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def check_password_rules(password, field="password"):
    """Shared password checks. Raises a DRF ValidationError keyed by `field`."""
    if len(password) < 8:
        raise serializers.ValidationError({field: "Password must be at least 8 characters long."})
    if not re.search(r"[a-zA-Z]", password) or not re.search(r"\d", password):
        raise serializers.ValidationError({field: "Password must contain both letters and digits."})
    try:
        validate_password(password)
    except DjangoValidationError as e:
        raise serializers.ValidationError({field: list(e.messages)})


class UserSerializer(serializers.ModelSerializer):
    """Basic user profile serializer."""

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name",
                  "user_type", "is_active", "is_staff"]
        read_only_fields = ["id", "is_active", "is_staff"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Registers new user, enforces password rules, and triggers verification OTP."""
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "username", "password", "confirm_password"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate_email(self, value):
        email = value.lower().strip()
        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        if User.objects.filter(email__iexact=email).exists():
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
        if password != data.get("confirm_password"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        check_password_rules(password)
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)

        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data.get("username"),  # optional, may be missing/None
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
            is_active=False,  # inactive until email verification
        )

        # Public signup always gets the default type (not client-controlled)
        if hasattr(user, "user_type"):
            user.user_type = UserTypeChoices.USER
            user.save(update_fields=["user_type"])

        # Send verification OTP. If email fails, the user can use "resend OTP".
        try:
            otp = set_user_otp(user)
            send_otp_email(user.id, otp, "account_verification")
        except Exception:
            logger.exception("Failed to send verification OTP to user id=%s", user.id)

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
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "user_type",
                  "is_active", "is_staff", "created_at", "updated_at"]
        read_only_fields = ["id", "email", "is_active", "is_staff"]


class LoginSerializer(serializers.Serializer):
    """Validates credentials and attaches the user (token generation happens in the view)."""
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = (attrs.get("email") or "").lower().strip()
        username = (attrs.get("username") or "").strip()
        password = attrs.get("password", "")

        identifier = email or username
        if not identifier:
            raise serializers.ValidationError("Please provide either an email or username")

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError(
                "Account is not active or not verified. Please check your email for verification instructions."
            )
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
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh": "Invalid or expired refresh token."})


class PasswordResetRequestSerializer(serializers.Serializer):
    """Sends a password reset OTP. Never reveals whether the email exists."""
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
            try:
                otp = set_user_otp(user)
                send_otp_email(user.id, otp, "password_reset")
            except Exception:
                logger.exception("Failed to send password reset OTP to user id=%s", user.id)
        return True


class CompletePasswordResetSerializer(serializers.Serializer):
    """Completes the password reset using an OTP."""
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
        if new_password != data.get("confirm_new_password"):
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        check_password_rules(new_password, field="new_password")
        return data

    def save(self):
        success = complete_password_reset(
            self.validated_data["email"],
            self.validated_data["otp"],
            self.validated_data["new_password"],
        )
        if not success:
            raise serializers.ValidationError({"detail": "Invalid, expired OTP, or reset request failed."})
        return True


class ResendOTPSerializer(serializers.Serializer):
    """Resends OTP for account verification (inactive) or password reset (active)."""
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()
        if not email_validator(email):
            raise serializers.ValidationError("Invalid email address format.")
        return email

    def save(self):
        email = self.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        # Always return True: don't reveal whether the email exists.
        if user:
            purpose = "password_reset" if user.is_active else "account_verification"
            try:
                otp = set_user_otp(user)
                send_otp_email(user.id, otp, purpose)
            except Exception:
                logger.exception("Failed to resend OTP to user id=%s", user.id)
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

        request = self.context.get("request")
        current_user = request.user if request else None
        query = User.objects.filter(username__iexact=value)
        if current_user and current_user.pk:
            query = query.exclude(pk=current_user.pk)
        if query.exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def update(self, instance, validated_data):
        # Only touch fields that were actually sent (works for PATCH too)
        for field in ("username", "first_name", "last_name"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
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

        if not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Your current password is incorrect."})
        if new_password != data.get("confirm_new_password"):
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        if old_password == new_password:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})
        check_password_rules(new_password, field="new_password")
        return data

    def save(self, **kwargs):
        user = self.context.get("request").user
        user.set_password(self.validated_data["new_password"])
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
        if User.objects.filter(email__iexact=new_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return new_email

    def validate(self, data):
        user = self.context.get("request").user
        if not user.check_password(data.get("password")):
            raise serializers.ValidationError({"password": "Your current password is incorrect."})
        return data

    def save(self, **kwargs):
        user = self.context.get("request").user
        user.email = self.validated_data["new_email"]
        user.is_active = False  # deactivate until the new email is verified
        user.save()

        try:
            otp = set_user_otp(user)
            send_otp_email(user.id, otp, "email_change_verification")
        except Exception:
            logger.exception("Failed to send email-change OTP to user id=%s", user.id)

        return user