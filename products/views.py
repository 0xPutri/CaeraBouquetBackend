from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from users.permissions import IsAdminOrReadOnly
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related('category').all() # Optimasi query (mencegah N+1)
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)