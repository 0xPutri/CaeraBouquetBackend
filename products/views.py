import requests
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer, OpenApiParameter, OpenApiTypes
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from urllib.parse import urlparse

recommendation_item_response = inline_serializer(
    name='RecommendationItemResponse',
    fields={
        'product_id': serializers.CharField(help_text='ID produk hasil rekomendasi.'),
        'name': serializers.CharField(help_text='Nama produk rekomendasi.'),
        'price': serializers.FloatField(help_text='Harga produk rekomendasi.'),
    },
)

recommendation_response = inline_serializer(
    name='RecommendationResponse',
    fields={
        'recommendations': serializers.ListField(
            child=serializers.DictField(),
            help_text='Daftar produk yang direkomendasikan oleh layanan machine learning.',
        ),
    },
)

@extend_schema_view(
    list=extend_schema(
        tags=['Katalog'],
        summary='Melihat daftar kategori produk',
        description='Endpoint publik untuk menampilkan seluruh kategori bouquet yang tersedia pada katalog.',
        responses={200: CategorySerializer},
    ),
    retrieve=extend_schema(
        tags=['Katalog'],
        summary='Melihat detail kategori produk',
        description='Endpoint publik untuk menampilkan detail satu kategori produk berdasarkan ID.',
        responses={200: CategorySerializer},
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Menyediakan endpoint baca untuk kategori produk.

    Viewset ini dipakai frontend untuk menampilkan daftar kategori
    bouquet yang tersedia pada katalog publik.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)

@extend_schema_view(
    list=extend_schema(
        tags=['Katalog'],
        summary='Melihat daftar produk bouquet',
        description='Endpoint publik untuk menampilkan daftar produk bouquet yang tersedia di katalog.',
        responses={200: ProductSerializer},
    ),
    retrieve=extend_schema(
        tags=['Katalog'],
        summary='Melihat detail produk bouquet',
        description='Endpoint publik untuk menampilkan detail satu produk bouquet berdasarkan ID.',
        responses={200: ProductSerializer},
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Menyediakan endpoint baca untuk katalog produk bouquet.

    Viewset ini menampilkan daftar produk beserta detail penting seperti
    kategori, deskripsi, harga, dan tautan gambar produk.
    """
    queryset = Product.objects.select_related('category').all() # Optimasi query untuk mencegah masalah N+1.
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)

@extend_schema(
    tags=['Rekomendasi ML'],
    summary='Mendapatkan rekomendasi produk',
    description='Endpoint ini meneruskan permintaan ke layanan machine learning. Gunakan salah satu parameter: `product_id` atau `event_type`.',
    parameters=[
        OpenApiParameter(name='product_id', description='ID produk acuan untuk mencari rekomendasi serupa. Contoh: `B004`.', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='event_type', description='Jenis acara untuk menghasilkan rekomendasi. Contoh: `birthday` atau `wedding`.', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='top_n', description='Jumlah maksimum rekomendasi yang ingin dikembalikan. Nilai bawaan: `5`.', required=False, type=OpenApiTypes.INT),
    ],
    responses={
        200: OpenApiResponse(
            response=recommendation_response,
            description='Daftar rekomendasi berhasil dikembalikan.',
        ),
        400: OpenApiResponse(description='Parameter `product_id` atau `event_type` belum diberikan.'),
        503: OpenApiResponse(description='Layanan machine learning sedang tidak tersedia.'),
    },
    examples=[
        OpenApiExample(
            'Contoh Respons Rekomendasi Berhasil',
            value={
                'recommendations': [
                    {'product_id': 'B004', 'name': 'Birthday Bouquet', 'price': 125000},
                    {'product_id': 'B010', 'name': 'Rose Premium Bouquet', 'price': 175000},
                ],
            },
            response_only=True,
            status_codes=['200'],
        ),
        OpenApiExample(
            'Contoh Respons Parameter Tidak Lengkap',
            value={'error': "Sertakan parameter 'product_id' atau 'event_type'."},
            response_only=True,
            status_codes=['400'],
        ),
    ],
)

class RecommendationView(APIView):
    """Mengambil rekomendasi produk dari layanan machine learning.

    View ini meneruskan parameter permintaan ke service ML, lalu
    menyesuaikan hasilnya agar konsisten dengan format respons backend.
    """

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        """Memproses permintaan rekomendasi berdasarkan produk atau acara.

        Args:
            request (Request): Objek request yang memuat query parameter.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons berisi daftar rekomendasi atau pesan galat.
        """
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