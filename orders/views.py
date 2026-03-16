from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Order, Transaction
from products.models import Product
from .serializers import OrderCreateSerializer, OrderListSerializer

class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('transactions__product').order_by('-created_at')
    
    @transaction.atomic # Memastikan database rollback jika terjadi error di tengah proses
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        product = get_object_or_404(Product, id=data['product_id'])
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
        product.save()

        return Response(
            {
                "order_id": order.id,
                "status": order.status
            },
            status=status.HTTP_201_CREATED
        )