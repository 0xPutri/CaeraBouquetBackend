import logging
import requests
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer, OpenApiParameter, OpenApiTypes
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from urllib.parse import urlparse
from requests.exceptions import JSONDecodeError

logger = logging.getLogger('products')
security_logger = logging.getLogger('caera.security')

recommendation_item_response = inline_serializer(
    name='RecommendationItemResponse',
    fields={
        'id': serializers.IntegerField(help_text='ID internal produk pada backend.', required=False, allow_null=True),
        'product_id': serializers.CharField(help_text='ID produk eksternal dari layanan machine learning (contoh: B001).'),
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
        description='Endpoint publik untuk menampilkan daftar produk bouquet yang tersedia di katalog. Mendukung pagination default, filter kategori, pencarian nama/deskripsi, serta pengurutan hasil.',
        parameters=[
            OpenApiParameter(
                name='page',
                description='Nomor halaman hasil pagination. Ukuran halaman mengikuti konfigurasi backend.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='category',
                description='Filter produk berdasarkan ID kategori.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='search',
                description='Cari produk berdasarkan nama atau deskripsi.',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='ordering',
                description='Urutkan hasil dengan `price`, `-price`, `created_at`, atau `-created_at`.',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
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
    kategori, deskripsi, harga, dan tautan gambar produk. Endpoint list
    juga mendukung pagination, filtering, pencarian, dan ordering.
    """
    queryset = Product.objects.select_related('category').all() # Optimasi query untuk mencegah masalah N+1.
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

@extend_schema(
    tags=['Rekomendasi ML'],
    summary='Mendapatkan rekomendasi produk',
    description='Endpoint ini meneruskan permintaan ke layanan machine learning. Gunakan salah satu parameter: `product_id` atau `event_type`.',
    parameters=[
        OpenApiParameter(name='product_id', description='ID produk acuan. Dapat berupa ID internal backend (contoh: `12`) atau ID eksternal ML (contoh: `B004`).', required=False, type=OpenApiTypes.STR),
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
                    {'id': 12, 'product_id': 'B004', 'name': 'Birthday Bouquet', 'price': 125000},
                    {'id': 24, 'product_id': 'B010', 'name': 'Rose Premium Bouquet', 'price': 175000},
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

    View ini meneruskan parameter permintaan ke layanan ML, lalu
    menyesuaikan hasilnya agar konsisten dengan format respons backend.
    """

    permission_classes = (AllowAny,)

    def _resolve_ml_product_id(self, product_id, request):
        """Maps internal product IDs to ML IDs while preserving existing error text."""
        if not product_id.isdigit():
            return product_id, None

        source_product = Product.objects.filter(id=int(product_id)).only('external_product_id').first()
        if source_product and source_product.external_product_id:
            return source_product.external_product_id, None

        security_logger.warning(
            "Permintaan rekomendasi ditolak karena external_product_id tidak tersedia.",
            extra={"product_id": product_id, "ip": request.META.get("REMOTE_ADDR")}
        )
        return None, Response(
            {"error": "Produk acuan tidak memiliki external_product_id untuk rekomendasi."},
            status=400
        )

    def _build_ml_url(self, request, product_id, event_type, top_n):
        """Builds the ML endpoint URL; validation stays isolated from response mapping."""
        ml_base_url = settings.ML_SERVICE_BASE_URL

        if product_id:
            ml_product_id, error_response = self._resolve_ml_product_id(product_id, request)
            if error_response is not None:
                return None, error_response
            return f"{ml_base_url}/api/recommendations/product/{ml_product_id}/?top_n={top_n}", None

        if event_type:
            return f"{ml_base_url}/api/recommendations/event/{event_type}/?top_n={top_n}", None

        return None, Response(
            {"error": "Sertakan parameter 'product_id' atau 'event_type'."},
            status=400
        )

    def _fetch_ml_recommendations(self, url):
        """Contains the external HTTP call so error handling in get() stays compact."""
        ml_base_url = settings.ML_SERVICE_BASE_URL

        with requests.Session() as session:
            host_header = urlparse(ml_base_url).netloc
            session.headers = {
                "Host": host_header,
                "Accept": "application/json"
            }

            response = session.get(url)
            response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("application/json"):
            raise requests.exceptions.RequestException(
                f"Tipe konten dari ML Service tidak valid: {content_type}"
            )

        return response.json().get('data', [])

    def _get_products_by_external_id(self, ml_data):
        """Fetches backend products in one query to avoid per-item lookups."""
        ml_product_ids = [item.get("product_id") for item in ml_data if item.get("product_id")]
        return {
            product.external_product_id: product
            for product in Product.objects.filter(external_product_id__in=ml_product_ids).only(
                "id",
                "external_product_id",
                "name",
                "price",
            )
        }

    def _format_recommendations(self, ml_data):
        """Normalizes ML items to the response contract expected by the backend API."""
        products_by_external_id = self._get_products_by_external_id(ml_data)
        recommendations = []

        for item in ml_data:
            ml_product_id = item.get("product_id")
            backend_product = products_by_external_id.get(ml_product_id)
            recommendations.append({
                "id": backend_product.id if backend_product else None,
                "product_id": ml_product_id,
                "name": backend_product.name if backend_product else item.get("product_type", "Rekomendasi Produk").title(),
                "price": float(backend_product.price) if backend_product else item.get("price", 0),
            })

        return recommendations

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

        url, error_response = self._build_ml_url(request, product_id, event_type, top_n)
        if error_response is not None:
            return error_response

        try:
            ml_data = self._fetch_ml_recommendations(url)
            recommendations = self._format_recommendations(ml_data)

            logger.info(
                "Permintaan rekomendasi berhasil diproses.",
                extra={
                    "ip": request.META.get("REMOTE_ADDR"),
                    "reference_product": product_id,
                    "event_type": event_type,
                    "result_count": len(recommendations)
                }
            )
        except JSONDecodeError:
            security_logger.exception(
                "ML Service mengembalikan JSON yang tidak valid.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
            return Response(
                {"error": "Respons ML Service tidak valid."},
                status=503
            )
        except requests.exceptions.RequestException as e:
            security_logger.exception(
                "Permintaan ke ML Service gagal diproses.",
                extra={"ip": request.META.get("REMOTE_ADDR"), "error": str(e)}
            )
            return Response(
                {"error": "ML Service sedang tidak tersedia."},
                status=503
            )

        return Response({"recommendations": recommendations})
