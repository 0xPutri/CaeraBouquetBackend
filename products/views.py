import requests
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from urllib.parse import urlparse

@extend_schema(tags=['Katalog'])
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Melihat daftar kategori produk bouquet."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)

@extend_schema(tags=['Katalog'])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Melihat daftar produk bouquet berserta detail harganya."""
    queryset = Product.objects.select_related('category').all() # Optimasi query (mencegah N+1)
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)

@extend_schema(
    tags=['Rekomendasi ML'],
    summary="Mendapatkan rekomendasi produk dari Machine Learning",
    description="Endpoint ini akan meneruskan permintaan ke Service ML. Gunakan salah satu parameter: `product_id` atau `event_type`.",
    parameters=[
        OpenApiParameter(name='product_id', description='ID Produk (Contoh: B004)', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='event_type', description='Kategori Acara (Contoh: birthday, wedding)', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='top_n', description='Jumlah rekomendasi maksimal (Default: 5)', required=False, type=OpenApiTypes.INT),
    ]
)

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
            
            with requests.Session() as session:
                host_header = urlparse(ml_base_url).netloc 
                session.headers = {
                    "Host": host_header,
                    "Accept": "application/json"
                }
                
                response = session.get(url)
                response.raise_for_status()

            ml_data = response.json().get('data', [])
            for item in ml_data:
                recommendations.append({
                    "product_id": item.get("product_id"), 
                    "name": item.get("product_type", "Rekomendasi Produk").title(), 
                    "price": item.get("price", 0)
                })
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] ML Service gagal diakses: {e}")
            return Response(
                {"error": "ML Service sedang tidak tersedia."},
                status=503
            )

        return Response({"recommendations": recommendations})