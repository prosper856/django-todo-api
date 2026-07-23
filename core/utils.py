from django.core.mail import send_mail
from django.conf import settings

def send_welcome_email(user_email, username):
    send_mail(
        subject="Welcome to Todo App",
        message=f"Hi {username},\n\nYour account has been successfully created. Welcome to Todo App!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list= [user_email],
        fail_silently=False,
    )