from rest_framework import serializers

from django.contrib.auth import get_user_model, authenticate
from apps.base.choices import UserTypeChoices, StatusChoices
from apps.base.account_utils import complete_password_reset, email_validator, get_tokens_for_user, send_otp_email, set_user_otp, initiate_password_reset
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "user_types", "is_active", "is_staff"]
        read_only_fields = ["id", "is_active", "is_staff"]


class UserDetialSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "user_types", "is_active", "is_staff"]
        read_only_fields = ["id", "email", "is_active", "is_staff"]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password", "confirm_password"]

        extra_kwargs = {
            "user_type": {"default": UserTypeChoices.USER},
            "is_active": {"default": False},
        }


    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format")
        return value.lower()

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        if len(data["password"]) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        validated_data["is_active"] = False
        user_type = validated_data.get("user_type", UserTypeChoices.USER)
        
        user = User.objects.create_user(
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name",""),
            password=validated_data["password"],
            is_active=False
        
        )
        user.user_type = user_type
        user.save()

        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "account verification")
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format")
        return value.lower()
    
    def validate(self, data):
        email = data.get("email", "")
        password = data.get("password", "")

        user = authenticate(request=self.context.get("request"), email=email, password=password)

        if user is None:
            try:
                user_obj = User.objects.get(email=email)
                self.check_usser_status(user_obj)
                raise serializers.ValidationError("Invalid credentials")
            except User.DoesNotExist:
                raise serializers.ValidationError("user does not exist")

        self.check_usser_status(user)

        tokens = get_tokens_for_user(user)
        return {"user": user, "tokens": tokens}
    

    def check_usser_status(self, user):
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive")
        if user.status == StatusChoices.PENDING:
            raise serializers.ValidationError("Account verification pending")
        if user.status == StatusChoices.BLOCKED:
            raise serializers.ValidationError("Account is blocked")
        if user.status == StatusChoices.DELETED:
            raise serializers.ValidationError("Account is deleted")


class UserUpadteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "user_types", "email")
        read_only_fields = ("email", "user_types")

        def update(self, instance, validated_data):
            instance = super().update(instance, validated_data)
            return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format")
        return value.lower()

    def save(self):
        email = self.validated_data['email']
        initiate_password_reset(email)
        return {
            "message": "If an account with the provided email exists, an OTP has been sent for password reset."
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    comfirm_new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        if data["new_password"] != data["comfirm_new_password"]:
            raise serializers.ValidationError("New passwords do not match")
        if len(data["new_password"]) < 8:
            raise serializers.ValidationError("New password must be at least 8 characters long")
        
        if not data["new_password"].isalnum():
            raise serializers.ValidationError("New password must contain both letters and numbers")
        return data

    def save(self, user):
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user

class CompletePasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only = True)
    otp = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format")
        return value.lower()

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError("New passwords do not match")
        if len(data["new_password"]) < 8:
            raise serializers.ValidationError("New password must be at least 8 characters long")
        if not data["new_password"].isalnum():
            raise serializers.ValidationError("New password must contain both letters and numbers")
        return data


    def save(self):
        email = self.validated_data["email"]
        otp = self.validated_data["otp"]
        new_password = self.validated_data["new_password"]
        success = complete_password_reset(email, otp, new_password)
        if not success:
            raise serializers.ValidationError("Failed to reset password. Please check your email and OTP.")
        return {"message": "Password reset successful"}
    


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email", "")
        otp = data.get("otp", "")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with the given email does not exist")

        if not user.otp or user.otp != otp:
            raise serializers.ValidationError("Invalid OTP")
        

        if user.otp_verified:
            raise serializers.ValidationError("OTP already verified")

        data["user"] = user
        return data
    



    