from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password"),
        }),
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",)}),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )
    ordering = ("email",)
    list_display = ("id", "email", "first_name", "last_name", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name")

# Register your models here.
