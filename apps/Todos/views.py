import uuid
from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Category, TodoItem
from .serializers import CategorySerializer, TodoItemSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_filter_fields", None) or self.request.user.is_anonymous:
            return Category.objects.none()
        user_id = self.kwargs.get("user_id")
        if user_id:
            try:
                parsed_uuid = uuid.UUID(user_id)
                return Category.objects.filter(user_id=parsed_uuid)
            except (ValueError, TypeError):
                return Category.objects.none()
        return Category.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
            serializer.save(user=self.request.user)

class TodoItemViewSet(viewsets.ModelViewSet):
    serializer_class = TodoItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, "swagger_filter_fields", None) or self.request.user.is_anonymous:
            return TodoItem.objects.none()

        return TodoItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)        


