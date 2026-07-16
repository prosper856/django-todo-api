from rest_framework import serializers
from .models import Category, TodoItem

class CategorySerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Category
        fields = ['id', "user", "name", "created_at"]


class TodoItemSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    category_detail = CategorySerializer(source="category", read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = TodoItem
        fields = [
            "id", "user", "title", "description", "category",
            "category_detail", "completed", "priority",
            "priority_display", "due_date","image", "created_at", "updated_at"
        ]