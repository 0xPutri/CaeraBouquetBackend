from rest_framework import serializers
from django.conf import settings
from drf_spectacular.utils import OpenApiTypes, extend_schema_field

from .models import Order, Transaction
from products.models import Product


class OrderItemSerializer(serializers.Serializer):
    """Memvalidasi item produk individu dalam sebuah pesanan."""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=settings.MAX_ORDER_QUANTITY,
    )


class OrderCreateSerializer(serializers.Serializer):
    """Memvalidasi data input untuk pembuatan pesanan baru.

    Serializer ini mendukung pembuatan pesanan tunggal (backward compatibility)
    maupun pesanan dengan banyak produk melalui field 'items'.
    """

    items = OrderItemSerializer(many=True, required=False)

    product_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=settings.MAX_ORDER_QUANTITY,
    )

    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """
        Memastikan setidaknya ada satu produk dalam data pesanan.

        Fungsi ini memeriksa keberadaan produk baik melalui format daftar item
        maupun format pesanan tunggal untuk menjaga validitas transaksi.

        Args:
            data (dict): Data input pesanan yang akan divalidasi.

        Returns:
            dict: Data yang telah divalidasi jika memenuhi syarat.

        Raises:
            ValidationError: Jika tidak ada produk yang ditemukan dalam request.
        """
        if not data.get('items') and not (data.get('product_id') and data.get('quantity')):
            raise serializers.ValidationError(
                "Pesanan harus memiliki setidaknya satu produk (melalui 'items' atau 'product_id')."
            )
        return data


class TransactionDetailSerializer(serializers.ModelSerializer):
    """
    Menyajikan detail item produk dalam sebuah transaksi.

    Serializer ini memberikan informasi spesifik mengenai nama produk,
    jumlah yang dibeli, serta harga satuan saat transaksi terjadi.
    """

    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Transaction
        fields = ('product_name', 'quantity', 'price')


class OrderListSerializer(serializers.ModelSerializer):
    """
    Menyajikan informasi pesanan untuk riwayat pengguna.

    Serializer ini menyediakan data lengkap mengenai daftar produk yang dibeli,
    total harga, status pesanan, serta waktu pembuatannya.
    """

    order_id = serializers.IntegerField(source='id')
    items = TransactionDetailSerializer(source='transactions', many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('order_id', 'items', 'total_price', 'status', 'created_at')