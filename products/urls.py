from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductViewSet, RecommendationView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    # Route ViewSets (Categories, Products)
    path('', include(router.urls)),

    # Route Rekomendasi ML
    path('recommendations/', RecommendationView.as_view(), name='recommendation-list'),
]