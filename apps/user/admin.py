from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "first_name", "last_name", "password"),
        }),
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ( "username","first_name", "last_name", "user_type")}),
        ("OTP & Verification", {"fields": ("otp", "otp_created_at", "otp_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",)}),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login")
    ordering = ("email",)
    list_display = ("id", "email", "username", "user_type", "is_active", "is_superuser")
    search_fields = ("email", "username", "first_name", "last_name")

# Register your models here.
