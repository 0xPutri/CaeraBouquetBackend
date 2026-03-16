from rest_framework import serializers
from .models import Order, Transaction
from products.models import Product

class OrderCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

class OrderListSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source='id')

    class Meta:
        model = Order
        fields = ('order_id', 'product_name', 'quantity', 'status', 'created_at')

    def get_product_name(self, obj):
        transaction = obj.transactions.first()
        return transaction.product.name if transaction and transaction.product else "Produk Tidak Diketahui"
    
    def get_quantity(self, obj):
        transaction = obj.transactions.first()
        return transaction.quantity if transaction else 0