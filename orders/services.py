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

ZERO_PRICE = Decimal('0.00')


def _get_locked_products_by_id(product_ids):
    """Centralizes product locking so order workflows use the same query shape."""
    return {
        product.id: product
        for product in Product.objects.select_for_update().filter(id__in=product_ids)
    }


def _ensure_order_total_allowed(user, total_price, log_message, extra=None):
    """Keeps the max-total business rule in one place without changing messages."""
    if total_price <= settings.MAX_ORDER_TOTAL_PRICE:
        return

    log_extra = {"user_id": str(user.id), "total_price": str(total_price)}
    if extra:
        log_extra.update(extra)

    security_logger.warning(log_message, extra=log_extra)
    raise ValidationError("Total harga pesanan melebihi batas maksimum yang diizinkan.")


def _create_order_record(*, user, total_price, delivery_address, notes):
    """Creates the order row consistently for single- and multi-item flows."""
    return Order.objects.create(
        user=user,
        total_price=total_price,
        delivery_address=delivery_address,
        notes=notes,
    )


def _create_transaction_and_reduce_stock(order, product, quantity):
    """Persists one transaction and applies the matching stock deduction."""
    Transaction.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=product.price,
    )

    product.stock -= quantity
    product.save(update_fields=['stock'])


def _quantity_by_product(transactions):
    """Aggregates quantities by product to make inventory diff logic easier to read."""
    quantities = {}
    for transaction_item in transactions:
        product_id = transaction_item.get('product_id') if isinstance(transaction_item, dict) else transaction_item.product_id
        quantity = transaction_item.get('quantity') if isinstance(transaction_item, dict) else transaction_item.quantity

        if product_id is None:
            continue
        quantities[product_id] = quantities.get(product_id, 0) + quantity
    return quantities


def _stock_delta(product_id, current_quantities, previous_quantities):
    """Returns the additional stock consumed by the edited order transaction set."""
    return current_quantities.get(product_id, 0) - previous_quantities.get(product_id, 0)

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
    products_map = _get_locked_products_by_id(product_ids)

    validated_items = []
    total_price = ZERO_PRICE

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
        })

    _ensure_order_total_allowed(
        user,
        total_price,
        "Pembuatan pesanan ditolak karena melebihi batas total harga.",
    )

    with transaction.atomic():
        order = _create_order_record(
            user=user,
            total_price=total_price,
            delivery_address=delivery_address,
            notes=notes,
        )

        for v_item in validated_items:
            _create_transaction_and_reduce_stock(order, v_item['product'], v_item['quantity'])

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
    _ensure_order_total_allowed(
        user,
        total_price,
        "Pembuatan pesanan ditolak di service karena melebihi batas total harga.",
        extra={"product_id": product_id},
    )

    order = _create_order_record(
        user=user,
        total_price=total_price,
        delivery_address=delivery_address,
        notes=notes,
    )

    _create_transaction_and_reduce_stock(order, product, quantity)

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

    current_quantity_by_product = _quantity_by_product(current_transactions)
    previous_quantity_by_product = _quantity_by_product(previous_snapshot.values())

    touched_product_ids = set(current_quantity_by_product) | set(previous_quantity_by_product)
    products = _get_locked_products_by_id(touched_product_ids)

    for product_id in touched_product_ids:
        stock_delta = _stock_delta(product_id, current_quantity_by_product, previous_quantity_by_product)
        if stock_delta > 0 and products[product_id].stock < stock_delta:
            security_logger.warning(
                "Sinkronisasi inventaris pesanan ditolak karena stok tidak mencukupi.",
                extra={"order_id": order.id, "product_id": product_id, "required_stock": stock_delta}
            )
            raise ValidationError("Stok tidak mencukupi untuk menyimpan perubahan transaksi admin.")

    for product_id in touched_product_ids:
        stock_delta = _stock_delta(product_id, current_quantity_by_product, previous_quantity_by_product)
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
    order.total_price = recalculated_total if current_transactions else ZERO_PRICE
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
