from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField
 

class Category(models.Model):
    user =models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ("user", "name")

    def __str__(self):
        return self.name
    



class TodoItem(models.Model):
    PRIORITY_CHOICES = [
        ("H", "High"),
        ("M", "Medium"),
        ("L", "Low"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='todos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True,null=True, related_name='todos')
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default="M")
    image = CloudinaryField('image', blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Todo Items"
        ordering = ["priority", '-created_at']

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"[{self.get_priority_display()}] {self.title} - {status}"   
