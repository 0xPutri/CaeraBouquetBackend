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


def get_locked_products_by_id(product_ids):
    """
    Mengambil data produk dan menguncinya untuk proses transaksi.

    Fungsi ini memastikan data produk diurutkan berdasarkan ID guna mencegah
    terjadinya kebuntuan (deadlock) saat ada banyak pesanan bersamaan.

    Args:
        product_ids (list): Daftar ID produk yang akan diambil.

    Returns:
        QuerySet: Kumpulan produk yang telah dikunci.
    """
    return Product.objects.select_for_update().filter(id__in=product_ids).order_by('id')


def ensure_order_total_allowed(total_price, user_id=None, log_message="Pembuatan pesanan ditolak karena melebihi batas total harga."):
    """
    Mengecek apakah total harga pesanan masih dalam batas aman.

    Fungsi ini memvalidasi total belanja agar tidak melampaui batas maksimal
    yang diizinkan oleh sistem.

    Args:
        total_price (Decimal): Total harga dari seluruh pesanan.
        user_id (str, optional): ID pengguna untuk kebutuhan pencatatan.
        log_message (str, optional): Pesan log jika validasi gagal.

    Raises:
        ValidationError: Jika total harga melebihi batas maksimum.
    """
    if total_price > settings.MAX_ORDER_TOTAL_PRICE:
        security_logger.warning(
            log_message,
            extra={"user_id": str(user_id) if user_id else None, "total_price": str(total_price)}
        )
        raise ValidationError("Total harga pesanan melebihi batas maksimum yang diizinkan.")


def create_order_record(user, total_price, delivery_address, notes):
    """
    Menyimpan data utama pesanan ke dalam database.

    Fungsi ini membuat satu baris catatan pesanan baru berdasarkan rincian
    yang diberikan oleh pengguna.

    Args:
        user (User): Pengguna yang melakukan pemesanan.
        total_price (Decimal): Total harga yang harus dibayar.
        delivery_address (str): Alamat tujuan pengiriman.
        notes (str): Catatan tambahan untuk pesanan.

    Returns:
        Order: Objek pesanan yang berhasil dibuat.
    """
    return Order.objects.create(
        user=user,
        total_price=total_price,
        delivery_address=delivery_address,
        notes=notes,
    )


def create_transaction_and_reduce_stock(order, product, quantity, price):
    """
    Mencatat rincian transaksi dan menyesuaikan ketersediaan stok.

    Fungsi ini membuat catatan untuk setiap item yang dibeli sekaligus
    mengurangi jumlah stok fisik produk di katalog.

    Args:
        order (Order): Objek pesanan utama.
        product (Product): Objek produk yang dibeli.
        quantity (int): Jumlah produk yang dipesan.
        price (Decimal): Harga satuan produk saat itu.
    """
    Transaction.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=price,
    )
    product.stock -= quantity
    product.save(update_fields=['stock'])


def quantity_by_product(transactions):
    """
    Menghitung total jumlah setiap produk dalam sebuah pesanan.

    Fungsi ini mengumpulkan dan menjumlahkan kuantitas dari daftar
    transaksi untuk mempermudah proses sinkronisasi.

    Args:
        transactions (list): Daftar transaksi yang akan dihitung.

    Returns:
        dict: Pemetaan antara ID produk dan total jumlahnya.
    """
    qty_map = {}
    for tx in transactions:
        if tx.product_id:
            qty_map[tx.product_id] = qty_map.get(tx.product_id, 0) + tx.quantity
    return qty_map


def stock_delta(current_qty, previous_qty):
    """
    Menghitung selisih jumlah stok untuk sinkronisasi inventaris.

    Fungsi ini membantu mengetahui berapa banyak stok yang harus dikembalikan
    atau dikurangi saat terjadi perubahan pesanan.

    Args:
        current_qty (int): Jumlah pesanan saat ini.
        previous_qty (int): Jumlah pesanan sebelumnya.

    Returns:
        int: Selisih kuantitas stok.
    """
    return current_qty - previous_qty


def snapshot_order_transactions(order):
    """
    Mengambil data riwayat transaksi dari sebuah pesanan.

    Fungsi ini merekam kondisi transaksi sebelum adanya perubahan, sehingga
    penyesuaian stok dapat dihitung secara akurat nantinya.

    Args:
        order (Order): Objek pesanan yang akan diambil datanya.

    Returns:
        dict: Peta data transaksi saat ini.
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
    """
    Memproses pembuatan pesanan untuk banyak produk sekaligus.

    Fungsi ini menjamin bahwa validasi stok, pencatatan transaksi, dan
    pembaruan inventaris dilakukan secara aman dalam satu kesatuan waktu.

    Args:
        user (User): Pengguna yang melakukan pemesanan.
        items (list): Daftar produk yang dibeli beserta jumlahnya.
        delivery_address (str, optional): Alamat tujuan pengiriman.
        notes (str, optional): Pesan tambahan dari pelanggan.

    Returns:
        Order: Objek pesanan yang berhasil diproses.

    Raises:
        ValidationError: Jika produk tidak valid atau stok habis.
    """
    if not items:
        raise ValidationError("Pesanan harus memiliki setidaknya satu produk.")

    product_ids = [item['product_id'] for item in items]
    products_queryset = get_locked_products_by_id(product_ids)
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

    ensure_order_total_allowed(total_price, user.id, "Pembuatan pesanan ditolak karena melebihi batas total harga.")

    with transaction.atomic():
        order = create_order_record(user, total_price, delivery_address, notes)

        for v_item in validated_items:
            create_transaction_and_reduce_stock(order, v_item['product'], v_item['quantity'], v_item['price'])

    logger.info(
        "Pesanan multi-item berhasil dibuat.",
        extra={"user_id": str(user.id), "order_id": order.id, "item_count": len(validated_items)}
    )
    return order


@transaction.atomic
def create_order_with_single_transaction(*, user, product_id, quantity, delivery_address='', notes=''):
    """
    Memproses pembuatan pesanan untuk satu jenis produk.

    Fungsi ini disediakan untuk mendukung alur pembelian sederhana, memastikan
    stok dan data transaksi tetap konsisten.

    Args:
        user (User): Pengguna yang melakukan pemesanan.
        product_id (int): ID dari produk yang akan dibeli.
        quantity (int): Jumlah produk yang dipesan.
        delivery_address (str, optional): Alamat tujuan pengiriman.
        notes (str, optional): Pesan tambahan dari pelanggan.

    Returns:
        tuple: Objek pesanan baru dan produk yang diperbarui.

    Raises:
        ValidationError: Jika stok tidak memenuhi permintaan.
    """
    product = get_object_or_404(
        get_locked_products_by_id([product_id]),
        id=product_id,
    )

    if product.stock < quantity:
        security_logger.warning(
            "Pembuatan pesanan ditolak di service karena stok tidak mencukupi.",
            extra={"user_id": str(user.id), "product_id": product_id, "requested_quantity": quantity}
        )
        raise ValidationError("Stok tidak mencukupi")

    total_price = product.price * quantity
    ensure_order_total_allowed(total_price, user.id, "Pembuatan pesanan ditolak di service karena melebihi batas total harga.")

    order = create_order_record(user, total_price, delivery_address, notes)
    create_transaction_and_reduce_stock(order, product, quantity, product.price)

    logger.info(
        "Pesanan satu item berhasil dibuat melalui service.",
        extra={"user_id": str(user.id), "order_id": order.id, "product_id": product.id, "quantity": quantity}
    )
    return order, product


@transaction.atomic
def sync_order_inventory(order, previous_snapshot):
    """
    Menyelaraskan data pesanan dengan inventaris terbaru.

    Fungsi ini merespons perubahan yang dilakukan oleh admin, memastikan
    bahwa selisih stok dan total harga dihitung ulang dengan presisi.

    Args:
        order (Order): Objek pesanan yang mengalami perubahan.
        previous_snapshot (dict): Kondisi pesanan sebelum diubah admin.

    Returns:
        Order: Objek pesanan yang telah disinkronisasi.

    Raises:
        ValidationError: Jika perubahan admin menyebabkan stok minus.
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

    current_quantity_by_product = quantity_by_product(current_transactions)
    previous_quantity_by_product = {}

    for previous_item in previous_snapshot.values():
        if previous_item['product_id'] is None:
            continue
        previous_quantity_by_product[previous_item['product_id']] = (
            previous_quantity_by_product.get(previous_item['product_id'], 0) + previous_item['quantity']
        )

    touched_product_ids = set(current_quantity_by_product) | set(previous_quantity_by_product)
    products = {
        product.id: product
        for product in get_locked_products_by_id(list(touched_product_ids))
    }

    for product_id in touched_product_ids:
        delta = stock_delta(current_quantity_by_product.get(product_id, 0), previous_quantity_by_product.get(product_id, 0))
        if delta > 0 and products[product_id].stock < delta:
            security_logger.warning(
                "Sinkronisasi inventaris pesanan ditolak karena stok tidak mencukupi.",
                extra={"order_id": order.id, "product_id": product_id, "required_stock": delta}
            )
            raise ValidationError("Stok tidak mencukupi untuk menyimpan perubahan transaksi admin.")

    for product_id in touched_product_ids:
        delta = stock_delta(current_quantity_by_product.get(product_id, 0), previous_quantity_by_product.get(product_id, 0))
        if delta == 0:
            continue
        product = products[product_id]
        product.stock -= delta
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