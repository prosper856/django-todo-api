from django.db import models


class StatusChoices(models.TextChoices):
    DEFAULT = "DEFAULT", "Default"
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    PENDING = "PENDING", "Pending"
    SUSPENDED = "SUSPENDED", "Suspended"
    DELETED = "DELETED", "Deleted"
    BLOCKED = "BLOCKED", "Blocked"


class UserTypeChoices(models.TextChoices):
    USER = "USER", "User"
    ADMIN = "ADMIN", "Admin"
    