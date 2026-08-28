import uuid
from rest_framework import viewsets, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import Category, TodoItem
from .serializers import CategorySerializer, TodoItemSerializer
from apps.base.permissions import IsAdminOrOwner

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", None) or self.request.user.is_anonymous:
            return Category.objects.none()
        if self.request.user.is_staff:
            return Category.objects.all()
        
        user_id = self.request.query_params.get("user_id")
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
    permission_classes = [IsAdminOrOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", None) or self.request.user.is_anonymous:
            return TodoItem.objects.none()
        if self.request.user.is_staff:
            return TodoItem.objects.all()
        return TodoItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)        


