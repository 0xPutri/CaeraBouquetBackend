import logging
from rest_framework import generics, status, filters
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.db import transaction, DatabaseError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view, inline_serializer
from .models import Order
from .services import create_order, create_order_with_single_transaction
from .throttles import OrderCreateUserRateThrottle
from .serializers import OrderCreateSerializer, OrderListSerializer

logger = logging.getLogger('orders')
security_logger = logging.getLogger('caera.security')

order_create_success_response = inline_serializer(
    name='OrderCreateSuccessResponse',
    fields={
        'order_id': serializers.IntegerField(help_text='ID pesanan yang berhasil dibuat.'),
        'status': serializers.CharField(help_text='Status awal pesanan setelah dibuat.'),
    },
)

@extend_schema_view(
    get=extend_schema(
        tags=['Pesanan'],
        summary='Melihat riwayat pesanan pengguna',
        description='Endpoint ini menampilkan daftar pesanan milik pengguna yang sedang login, diurutkan dari yang terbaru. Mendukung pagination default, filter status, pencarian nama produk, dan pengurutan hasil.',
        parameters=[
            OpenApiParameter(
                name='page',
                description='Nomor halaman hasil pagination. Ukuran halaman mengikuti konfigurasi backend.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='status',
                description='Filter pesanan berdasarkan status, misalnya `created`, `paid`, atau `cancelled`.',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='search',
                description='Cari pesanan berdasarkan nama produk pada transaksi.',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='ordering',
                description='Urutkan hasil dengan `created_at`, `-created_at`, `total_price`, atau `-total_price`.',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={
            200: OrderListSerializer,
            401: OpenApiResponse(description='Autentikasi diperlukan untuk melihat riwayat pesanan.'),
        },
        examples=[
            OpenApiExample(
                'Contoh Respons Riwayat Pesanan',
                value=[
                    {
                        'order_id': 12,
                        'items': [
                            {
                                'product_name': 'Rose Bouquet Deluxe',
                                'quantity': 2,
                                'price': '150000.00'
                            },
                            {
                                'product_name': 'Lily Bouquet White',
                                'quantity': 1,
                                'price': '85000.00'
                            }
                        ],
                        'total_price': '385000.00',
                        'status': 'created',
                        'created_at': '2026-03-24T23:40:00+07:00',
                    }
                ],
                response_only=True,
                status_codes=['200'],
            ),
        ],
    ),
    post=extend_schema(
        tags=['Pesanan'],
        summary='Membuat pesanan baru',
        description='Endpoint ini membuat pesanan baru untuk satu atau lebih produk, mencatat transaksi, dan mengurangi stok produk secara atomik.',
        request=OrderCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=order_create_success_response,
                description='Pesanan berhasil dibuat.',
            ),
            400: OpenApiResponse(description='Data pesanan tidak valid atau stok tidak mencukupi.'),
            401: OpenApiResponse(description='Autentikasi diperlukan untuk membuat pesanan.'),
        },
        examples=[
            OpenApiExample(
                'Contoh Request Pesanan Banyak Produk',
                value={
                    'items': [
                        {'product_id': 3, 'quantity': 2},
                        {'product_id': 5, 'quantity': 1}
                    ],
                    'delivery_address': 'Jl. Melati No. 8, Jakarta',
                    'notes': 'Mohon dikirim sebelum pukul 17.00',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Contoh Request Pesanan Tunggal (Legacy)',
                value={
                    'product_id': 3,
                    'quantity': 2,
                    'delivery_address': 'Jl. Melati No. 8, Jakarta',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Contoh Respons Pesanan Berhasil',
                value={
                    'order_id': 12,
                    'status': 'created',
                },
                response_only=True,
                status_codes=['201'],
            ),
            OpenApiExample(
                'Contoh Respons Stok Tidak Cukup',
                value={
                    'detail': 'Stok produk \'Rose Bouquet\' tidak mencukupi',
                },
                response_only=True,
                status_codes=['400'],
            ),
        ],
    ),
)
class OrderListCreateView(generics.ListCreateAPIView):
    """Menampilkan riwayat pesanan dan membuat pesanan baru.

    View ini menangani pembuatan pesanan pengguna, mendukung satu 
    atau banyak produk dalam satu transaksi yang bersifat atomik.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Order.objects.none()

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['transactions__product__name']
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']

    def get_throttles(self):
        """Menerapkan pembatasan request khusus untuk pembuatan pesanan.

        Returns:
            list: Daftar throttle yang sesuai dengan metode request aktif.
        """
        if self.request.method == 'POST':
            return [OrderCreateUserRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        """Memilih serializer sesuai metode HTTP yang digunakan.

        Returns:
            type[Serializer]: Serializer untuk proses baca atau tulis pesanan.
        """
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        """Mengambil daftar pesanan milik pengguna yang sedang login.

        Returns:
            QuerySet: Query pesanan yang sudah diurutkan dari terbaru.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        logger.info(
            "Riwayat pesanan pengguna diminta.",
            extra={"user_id": str(self.request.user.id)}
        )
        return Order.objects.filter(user=self.request.user).prefetch_related('transactions__product')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Memproses pembuatan pesanan baru bagi pengguna.

        Metode ini menangani validasi data, pembuatan transaksi, hingga
        pengurangan stok produk secara aman dan menyeluruh.

        Args:
            request (Request): Objek request yang memuat detail pesanan.
            *args: Argumen tambahan untuk pemrosesan view.
            **kwargs: Argumen keyword untuk pemrosesan view.

        Returns:
            Response: Informasi nomor pesanan dan status keberhasilan.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            security_logger.warning(
                "Validasi pembuatan pesanan gagal.",
                extra={"user_id": str(request.user.id), "errors": serializer.errors}
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        items = data.get('items')
        if not items:
            items = [{'product_id': data['product_id'], 'quantity': data['quantity']}]

        try:
            with transaction.atomic():
                order = create_order(
                    user=request.user,
                    items=items,
                    delivery_address=data.get('delivery_address', ''),
                    notes=data.get('notes', ''),
                )
        except ValidationError as exc:
            error_message = exc.messages[0] if exc.messages else str(exc)
            security_logger.warning(
                "Pembuatan pesanan ditolak karena validasi bisnis gagal.",
                extra={"user_id": str(request.user.id), "items": items}
            )
            return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            security_logger.exception(
                "Pembuatan pesanan gagal karena gangguan database.",
                extra={"user_id": str(request.user.id)}
            )
            return Response(
                {"detail": "Terjadi gangguan pada sistem. Silakan coba lagi."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        logger.info(
            "Pesanan berhasil dibuat.",
            extra={"user_id": str(request.user.id), "order_id": order.id, "item_count": len(items)}
        )

        return Response(
            {
                "order_id": order.id,
                "status": order.status
            },
            status=status.HTTP_201_CREATED
        )