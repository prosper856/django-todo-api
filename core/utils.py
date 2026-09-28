from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user_email, username=None, first_name=None):
    name = first_name or username or user_email.split("@")[0]
    send_mail(
        subject="Welcome to Todo App",
        message=f"Hi {name},\n\nYour account has been successfully created. Welcome to Todo App!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )