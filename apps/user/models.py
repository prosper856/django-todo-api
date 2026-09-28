from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.base.choices import UserTypeChoices
from apps.base.models import BaseModel

from .managers import UserManager


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    user_type = models.CharField(
        max_length=20,
        choices=UserTypeChoices.choices,
        default=UserTypeChoices.USER,
    )
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password are enough for createsuperuser

    objects = UserManager()

    def __str__(self):
        return self.username or self.email

    def save(self, *args, **kwargs):
        # Store blank usernames as NULL so the unique constraint never
        # collides on multiple empty strings (e.g. from admin or shell).
        if not self.username:
            self.username = None
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]