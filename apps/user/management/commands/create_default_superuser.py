import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from environment variables if it doesn't exist"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").lower().strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write("Superuser env vars not set, skipping.")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write("Superuser already exists, skipping.")
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            otp_verified=True,
        )
        self.stdout.write("Superuser created.")