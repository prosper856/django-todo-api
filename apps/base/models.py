from django.db import models
import uuid
from .choices import UserTypeChoices, StatusChoices

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DEFAULT)

    class Meta:
        abstract = True