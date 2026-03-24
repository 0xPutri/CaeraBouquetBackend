from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from .models import Order, Transaction
from products.models import Product
from .serializers import OrderCreateSerializer, OrderListSerializer

@extend_schema_view(
    get=extend_schema(
        tags=['Pesanan'],
        summary='Melihat riwayat pesanan pengguna',
        description='Endpoint ini menampilkan daftar pesanan milik pengguna yang sedang login, diurutkan dari yang terbaru.',
        responses={
            200: OrderListSerializer,
            401: OpenApiResponse(description='Autentikasi diperlukan untuk melihat riwayat pesanan.'),
        },
    ),
    post=extend_schema(
        tags=['Pesanan'],
        summary='Membuat pesanan baru',
        description='Endpoint ini membuat pesanan baru untuk satu produk, mencatat transaksi, dan mengurangi stok produk secara atomik.',
        request=OrderCreateSerializer,
        responses={
            201: OpenApiResponse(description='Pesanan berhasil dibuat.'),
            400: OpenApiResponse(description='Data pesanan tidak valid atau stok tidak mencukupi.'),
            401: OpenApiResponse(description='Autentikasi diperlukan untuk membuat pesanan.'),
        },
    ),
)
class OrderListCreateView(generics.ListCreateAPIView):
    """Menampilkan riwayat pesanan dan membuat pesanan baru.

    View ini menggabungkan kebutuhan daftar pesanan pengguna dengan alur
    checkout sederhana untuk satu produk dalam satu transaksi.
    """

    permission_classes = (IsAuthenticated,)

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
        return Order.objects.filter(user=self.request.user).prefetch_related('transactions__product').order_by('-created_at')
    
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
                {"detail": f"Stok tidak mencukupi. Sisa stok: {product.stock}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_price = product.price * quantity

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