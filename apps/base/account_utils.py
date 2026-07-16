import re
import secrets
import string

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def email_validator(email: str) -> bool:
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))

def set_user_otp(user, length: int = 6) -> str:
    otp = generate_otp(length)
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.otp_verified = False
    user.save(update_fields=["otp", "otp_created_at", "otp_verified"])
    return otp

def clear_user_otp(user):
    user.otp = None
    user.otp_created_at = None
    user.save(update_fields=["otp", "otp_created_at"])


def verfiy_user_otp(user, otp: str) -> bool:
    
    if not user.otp or user.otp != otp:
        return False
    
    if not user.otp_created_at:
        return False
    
    expiry_time = user.otp_created_at + timezone.timedelta(minutes=15)
    if timezone.now() > expiry_time:
        return False
    
    user.otp_verified = True
    user.save(update_fields=["otp_verified"])
    return True

def send_otp_email(user_id: int, otp: str, purpose: str):
    try:
        if isinstance(user_id, User):
            user = user_id
        else:
            user = User.objects.get(id=user_id)
            
        subject = f"Your OTP for {purpose}"
        context = {
            "user": user,
            "otp": otp,
            "purpose": purpose,
            "expiry": "5 minutes"    
        }
        template_path = "emails/otp_email.html"
        html_message = render_to_string(template_path, context)
        
        # ✅ Correct way: Import and use EmailMessage class
        from django.core.mail import EmailMessage
        
        email_message = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email_message.content_subtype = "html"  # Set content type to HTML
        email_message.send()
        
    except User.DoesNotExist:
        raise ValueError("User with the given ID does not exist.")
    except Exception as e:
        raise RuntimeError(f"Failed to send OTP email: {str(e)}")

def get_tokens_for_user(user):
    
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


def initiate_password_reset(email):
    """
    Initiate password reset process by generating and sending OTP.
    
    Finds an active user by email, generates an OTP, and sends it via email
    for password reset verification.
    
    Args:
        email (str): User's email address to initiate password reset for.
        
    Returns:
        str or None: Generated OTP string if successful, None if failed.
        
    Process Flow:
        1. Normalizes email (lowercase, stripped whitespace)
        2. Finds active user (excludes DELETED status, requires is_active=True)
        3. Generates and sets OTP for user
        4. Sends OTP email with "password reset" purpose
        5. Returns OTP on success, None on failure
        
    User Filtering:
        - Excludes users with status='DELETED'
        - Only includes users with is_active=True
        - Case-insensitive email matching
        
    Example:
        >>> otp = initiate_password_reset("user@example.com")
        >>> if otp:
        ...     print("Password reset initiated, OTP sent")
        ... else:
        ...     print("Failed to initiate password reset")
        
    Note:
        Returns None for any failure (user not found, email sending failure)
        to avoid revealing user existence.
    """
    try:
        user = User.objects.exclude(status='DELETED').get(email=email.lower().strip(), is_active=True)
        otp = set_user_otp(user)
        if send_otp_email(user.id, otp, "password reset"):
            return otp
        return None
    except User.DoesNotExist:
        return None
    except Exception as e:
        return None

def complete_password_reset(email, otp, new_password):
    try:
        user = User.objects.exclude(status='DELETED').get(email=email.lower().strip(), is_active=True)
        if not verfiy_user_otp(user, otp):
            return False
        user.set_password(new_password)
        user.save(update_fields=["password"])
        clear_user_otp(user)
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        return False