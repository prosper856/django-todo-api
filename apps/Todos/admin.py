from django.contrib import admin
from .models import Category, TodoItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user","created_at")
    list_filter = ("user",)
    search_fields = ("name", 'user__username')

@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ("id", 'title', "user","category", "priority", "completed", "due_date")
    list_display_links = ("id", "title")
    list_filter = ("completed", "priority", "user", "category", "due_date")
    search_fields = ("title", "description", "user__username","category__name")
    fieldsets = (
        ("Task Core Info",{
            "fields": ("user", "title", "description", "category")
        }),
        ("status & Urgency", {
            "fields": ("completed", "priority")
        }),
        ("Deadlines", {
            "fields": ("due_date",)
        }),
    )
                     
