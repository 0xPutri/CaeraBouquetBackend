from rest_framework import generics, status, filters
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view, inline_serializer
from .models import Order, Transaction
from .throttles import OrderCreateUserRateThrottle
from products.models import Product
from .serializers import OrderCreateSerializer, OrderListSerializer

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
                        'product_name': 'Rose Bouquet Deluxe',
                        'quantity': 2,
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
        description='Endpoint ini membuat pesanan baru untuk satu produk, mencatat transaksi, dan mengurangi stok produk secara atomik.',
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
                'Contoh Request Membuat Pesanan',
                value={
                    'product_id': 3,
                    'quantity': 2,
                    'delivery_address': 'Jl. Melati No. 8, Jakarta',
                    'notes': 'Mohon dikirim sebelum pukul 17.00',
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
                    'detail': 'Stok tidak mencukupi',
                },
                response_only=True,
                status_codes=['400'],
            ),
        ],
    ),
)
class OrderListCreateView(generics.ListCreateAPIView):
    """Menampilkan riwayat pesanan dan membuat pesanan baru.

    View ini menggabungkan kebutuhan daftar pesanan pengguna dengan alur
    checkout sederhana untuk satu produk dalam satu transaksi.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Order.objects.none()

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['transactions__product__name']
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']

    def get_throttles(self):
        """Menerapkan throttling khusus pada endpoint pembuatan pesanan."""
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
        return Order.objects.filter(user=self.request.user).prefetch_related('transactions__product')
    
    @transaction.atomic # Memastikan rollback database jika terjadi galat di tengah proses.
    def create(self, request, *args, **kwargs):
        """Membuat pesanan baru sekaligus memperbarui stok produk.

        Args:
            request (Request): Objek request yang memuat data pesanan.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons sukses pembuatan pesanan atau pesan validasi.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        product = get_object_or_404(
            Product.objects.select_for_update(),
            id=data['product_id']
        )
        quantity = data['quantity']

        if product.stock < quantity:
            return Response(
                {"detail": "Stok tidak mencukupi"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_price = product.price * quantity
        if total_price > settings.MAX_ORDER_TOTAL_PRICE:
            return Response(
                {"detail": "Total harga pesanan melebihi batas maksimum yang diizinkan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
            delivery_address=data.get('delivery_address', ''),
            notes=data.get('notes', '')
        )

        Transaction.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price
        )

        product.stock -= quantity
        product.save(update_fields=['stock'])

        return Response(
            {
                "order_id": order.id,
                "status": order.status
            },
            status=status.HTTP_201_CREATED
        )