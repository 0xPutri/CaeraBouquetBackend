from rest_framework import serializers
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from .models import Order, Transaction
from products.models import Product

class OrderCreateSerializer(serializers.Serializer):
    """Memvalidasi data input untuk pembuatan pesanan baru.

    Serializer ini menerima informasi dasar pesanan yang dibutuhkan
    backend sebelum transaksi disimpan ke database.
    """

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

class OrderListSerializer(serializers.ModelSerializer):
    """Menyajikan ringkasan pesanan pada halaman riwayat pengguna.

    Serializer ini menyederhanakan data order dengan menampilkan produk
    pertama, jumlah item, status, dan waktu pembuatan pesanan.
    """

    product_name = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source='id')

    class Meta:
        model = Order
        fields = ('order_id', 'product_name', 'quantity', 'status', 'created_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_product_name(self, obj) -> str:
        """Mengambil nama produk pertama dari transaksi pesanan.

        Args:
            obj (Order): Objek pesanan yang sedang diserialisasi.

        Returns:
            str: Nama produk pertama atau fallback jika data tidak tersedia.
        """
        transaction = obj.transactions.first()
        return transaction.product.name if transaction and transaction.product else "Produk Tidak Diketahui"
    
    @extend_schema_field(OpenApiTypes.INT)
    def get_quantity(self, obj) -> int:
        """Mengambil jumlah item dari transaksi pertama pada pesanan.

        Args:
            obj (Order): Objek pesanan yang sedang diserialisasi.

        Returns:
            int: Jumlah item pada transaksi pertama atau `0` bila kosong.
        """
        transaction = obj.transactions.first()
        return transaction.quantity if transaction else 0