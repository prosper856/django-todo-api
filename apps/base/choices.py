from django.db import models


class StatusChoices(models.TextChoices):
    DEFAULT = "default", "Default"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    PENDING = "pending", "Pending"
    SUSPENDED = "suspended", "Suspended"
    DELETED = "deleted", "Deleted"
    BLOCKED = "blocked", "Blocked"
    
    
class UserTypeChoices(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"
    STAFF = "staff", "Staff"
    