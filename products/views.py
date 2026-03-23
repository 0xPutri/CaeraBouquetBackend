import requests
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
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

class RecommendationView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        product_id = request.query_params.get('product_id')
        event_type = request.query_params.get('event_type')
        top_n = request.query_params.get('top_n', 5)

        recommendations = []
        ml_base_url = settings.ML_SERVICE_BASE_URL

        try:
            if product_id:
                url = f"{ml_base_url}/api/recommendations/product/{product_id}/?top_n={top_n}"
            elif event_type:
                url = f"{ml_base_url}/api/recommendations/event/{event_type}/?top_n={top_n}"
            else:
                return Response(
                    {"error": "Sertakan parameter 'product_id' atau 'event_type'."}, 
                    status=400
                )
            
            response = requests.get(url, timeout=60)

            if response.status_code == 200:
                ml_data = response.json().get('data', [])
                for item in ml_data:
                    recommendations.append({
                        "product_id": item.get("product_id"), 
                        "name": item.get("product_type", "Rekomendasi Produk").title(), 
                        "price": item.get("price", 0)
                    })
        except request.exceptions.RequestException as e:
            print(f"[ERROR] ML Service gagal diakses: {e}")

        return Response({"recommendations": recommendations})