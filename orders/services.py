import logging
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from products.models import Product
from .models import Order, Transaction

logger = logging.getLogger('orders')
security_logger = logging.getLogger('caera.security')

def snapshot_order_transactions(order):
    """Mengambil snapshot transaksi pesanan yang sedang tersimpan.

    Fungsi ini dipakai untuk membandingkan kondisi transaksi sebelum dan
    sesudah perubahan agar penyesuaian stok dapat dihitung dengan tepat.

    Args:
        order (Order): Pesanan yang akan diambil snapshotnya.

    Returns:
        dict: Snapshot transaksi.
    """
    if not order.pk:
        logger.debug(
            "Snapshot transaksi dilewati karena pesanan belum tersimpan.",
            extra={"order_id": None}
        )
        return {}

    snapshot = {
        transaction_item.pk: {
            'product_id': transaction_item.product_id,
            'quantity': transaction_item.quantity,
            'price': transaction_item.price,
        }
        for transaction_item in order.transactions.all()
    }
    logger.debug(
        "Snapshot transaksi pesanan berhasil diambil.",
        extra={"order_id": order.id, "transaction_count": len(snapshot)}
    )
    return snapshot

def create_order(*, user, items, delivery_address='', notes=''):
    """Membuat pesanan dengan banyak produk secara atomik.

    Args:
        user (User): Pengguna yang membuat pesanan.
        items (list): Daftar dict berisi 'product_id' dan 'quantity'.
        delivery_address (str): Alamat pengiriman.
        notes (str): Catatan tambahan.

    Returns:
        Order: Objek pesanan baru.

    Raises:
        ValidationError: Jika stok tidak cukup atau aturan bisnis dilanggar.
    """
    if not items:
        raise ValidationError("Pesanan harus memiliki setidaknya satu produk.")

    product_ids = [item['product_id'] for item in items]
    products_queryset = Product.objects.select_for_update().filter(id__in=product_ids)
    products_map = {p.id: p for p in products_queryset}

    validated_items = []
    total_price = Decimal('0.00')

    for item in items:
        p_id = item['product_id']
        qty = item['quantity']
        
        if p_id not in products_map:
            raise ValidationError(f"Produk dengan ID {p_id} tidak ditemukan.")
        
        product = products_map[p_id]
        if product.stock < qty:
            security_logger.warning(
                "Pembuatan pesanan ditolak karena stok tidak mencukupi.",
                extra={"user_id": str(user.id), "product_id": p_id, "requested_quantity": qty}
            )
            raise ValidationError(f"Stok produk '{product.name}' tidak mencukupi.")
        
        item_total = product.price * qty
        total_price += item_total
        validated_items.append({
            'product': product,
            'quantity': qty,
            'price': product.price
        })

    if total_price > settings.MAX_ORDER_TOTAL_PRICE:
        security_logger.warning(
            "Pembuatan pesanan ditolak karena melebihi batas total harga.",
            extra={"user_id": str(user.id), "total_price": str(total_price)}
        )
        raise ValidationError("Total harga pesanan melebihi batas maksimum yang diizinkan.")

    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            delivery_address=delivery_address,
            notes=notes,
        )

        for v_item in validated_items:
            Transaction.objects.create(
                order=order,
                product=v_item['product'],
                quantity=v_item['quantity'],
                price=v_item['price'],
            )
            
            v_item['product'].stock -= v_item['quantity']
            v_item['product'].save(update_fields=['stock'])

    logger.info(
        "Pesanan multi-item berhasil dibuat.",
        extra={"user_id": str(user.id), "order_id": order.id, "item_count": len(validated_items)}
    )
    return order

def create_order_with_single_transaction(*, user, product_id, quantity, delivery_address='', notes=''):
    """Membuat pesanan satu produk dan memperbarui stok secara atomik.

    Fungsi ini dipakai pada alur checkout sederhana agar pembuatan order,
    pencatatan transaksi, dan pengurangan stok tetap berjalan konsisten.

    Args:
        user (User): Pengguna yang membuat pesanan.
        product_id (int): ID produk yang ingin dipesan.
        quantity (int): Jumlah produk yang diminta.
        delivery_address (str): Alamat pengiriman pesanan.
        notes (str): Catatan tambahan dari pengguna.

    Returns:
        tuple[Order, Product]: Objek pesanan baru dan produk yang diperbarui.

    Raises:
        ValidationError: Jika pesanan tidak memenuhi aturan bisnis.
    """
    product = get_object_or_404(
        Product.objects.select_for_update(),
        id=product_id,
    )

    if product.stock < quantity:
        security_logger.warning(
            "Pembuatan pesanan ditolak di service karena stok tidak mencukupi.",
            extra={"user_id": str(user.id), "product_id": product_id, "requested_quantity": quantity}
        )
        raise ValidationError("Stok tidak mencukupi")

    total_price = product.price * quantity
    if total_price > settings.MAX_ORDER_TOTAL_PRICE:
        security_logger.warning(
            "Pembuatan pesanan ditolak di service karena melebihi batas total harga.",
            extra={"user_id": str(user.id), "product_id": product_id, "total_price": str(total_price)}
        )
        raise ValidationError("Total harga pesanan melebihi batas maksimum yang diizinkan.")

    order = Order.objects.create(
        user=user,
        total_price=total_price,
        delivery_address=delivery_address,
        notes=notes,
    )

    Transaction.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=product.price,
    )

    product.stock -= quantity
    product.save(update_fields=['stock'])

    logger.info(
        "Pesanan satu item berhasil dibuat melalui service.",
        extra={"user_id": str(user.id), "order_id": order.id, "product_id": product.id, "quantity": quantity}
    )
    return order, product

@transaction.atomic
def sync_order_inventory(order, previous_snapshot):
    """Menyelaraskan transaksi pesanan dengan stok dan total harga terbaru.

    Fungsi ini digunakan setelah perubahan transaksi admin agar harga
    item, total pesanan, dan stok produk tetap sinkron dengan data akhir.

    Args:
        order (Order): Objek pesanan yang sedang diselaraskan.
        previous_snapshot (dict): Snapshot transaksi sebelum perubahan dilakukan.

    Returns:
        Order: Objek pesanan yang telah diperbarui total harganya.

    Raises:
        ValidationError: Jika perubahan transaksi membuat stok tidak mencukupi.
    """
    logger.debug(
        "Sinkronisasi inventaris pesanan dimulai.",
        extra={"order_id": order.id}
    )
    current_transactions = list(order.transactions.select_related('product').all())
    current_quantity_by_product = {}
    previous_quantity_by_product = {}

    for transaction_item in current_transactions:
        if transaction_item.product_id is None:
            continue

        previous_item = previous_snapshot.get(transaction_item.pk)
        should_refresh_price = (
            previous_item is None
            or previous_item['product_id'] != transaction_item.product_id
            or transaction_item.price in (None, '')
        )
        if should_refresh_price:
            transaction_item.price = transaction_item.product.price
            transaction_item.save(update_fields=['price'])

        current_quantity_by_product[transaction_item.product_id] = (
            current_quantity_by_product.get(transaction_item.product_id, 0) + transaction_item.quantity
        )

    for previous_item in previous_snapshot.values():
        if previous_item['product_id'] is None:
            continue
        previous_quantity_by_product[previous_item['product_id']] = (
            previous_quantity_by_product.get(previous_item['product_id'], 0) + previous_item['quantity']
        )

    touched_product_ids = set(current_quantity_by_product) | set(previous_quantity_by_product)
    products = {
        product.id: product
        for product in Product.objects.select_for_update().filter(id__in=touched_product_ids)
    }

    for product_id in touched_product_ids:
        stock_delta = current_quantity_by_product.get(product_id, 0) - previous_quantity_by_product.get(product_id, 0)
        if stock_delta > 0 and products[product_id].stock < stock_delta:
            security_logger.warning(
                "Sinkronisasi inventaris pesanan ditolak karena stok tidak mencukupi.",
                extra={"order_id": order.id, "product_id": product_id, "required_stock": stock_delta}
            )
            raise ValidationError("Stok tidak mencukupi untuk menyimpan perubahan transaksi admin.")

    for product_id in touched_product_ids:
        stock_delta = current_quantity_by_product.get(product_id, 0) - previous_quantity_by_product.get(product_id, 0)
        if stock_delta == 0:
            continue
        product = products[product_id]
        product.stock -= stock_delta
        product.save(update_fields=['stock'])

    recalculated_total = sum(
        transaction_item.price * transaction_item.quantity
        for transaction_item in current_transactions
        if transaction_item.price is not None
    )
    order.total_price = recalculated_total if current_transactions else Decimal('0.00')
    order.save(update_fields=['total_price'])

    logger.info(
        "Sinkronisasi inventaris pesanan berhasil diselesaikan.",
        extra={
            "order_id": order.id,
            "transaction_count": len(current_transactions),
            "total_price": str(order.total_price),
        }
    )
    return order