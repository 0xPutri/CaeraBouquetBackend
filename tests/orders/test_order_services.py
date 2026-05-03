import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from products.models import Product, Category
from orders.models import Order, Transaction
from orders.services import create_order

User = get_user_model()

@pytest.fixture
def order_setup(db):
    """
    Menyiapkan data awal untuk pengujian transaksi.

    Fungsi ini menyediakan objek pengguna, kategori, serta beberapa produk
    dasar yang diperlukan dalam skenario pemesanan.
    """
    user = User.objects.create_user(
        email='hanna@caerabouquet.com',
        name='Hanna Fernanda',
        password='Password123!'
    )
    category = Category.objects.create(name='Test Category')
    product1 = Product.objects.create(
        category=category,
        name='Product 1',
        price=Decimal('100.00'),
        stock=10
    )
    product2 = Product.objects.create(
        category=category,
        name='Product 2',
        price=Decimal('200.00'),
        stock=5
    )
    return user, product1, product2

@pytest.mark.django_db
class TestOrderService:
    """
    Menguji keandalan fungsi layanan pembuatan pesanan.

    Kelas ini memvalidasi apakah logika bisnis seperti pengurangan stok
    dan perhitungan harga total berjalan dengan benar.
    """

    def test_create_order_success_multi_items(self, order_setup):
        """
        Memastikan pesanan dengan banyak produk dapat diproses.

        Pengujian ini memverifikasi bahwa sistem mampu menangani daftar item
        secara sekaligus dan memperbarui stok masing-masing produk.
        """
        user, p1, p2 = order_setup
        items = [
            {'product_id': p1.id, 'quantity': 2},
            {'product_id': p2.id, 'quantity': 1}
        ]
        
        order = create_order(
            user=user,
            items=items,
            delivery_address='Jl. Test No. 1',
            notes='Test notes'
        )
        
        assert order.transactions.count() == 2
        assert order.total_price == Decimal('400.00')
        
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.stock == 8
        assert p2.stock == 4

    def test_create_order_insufficient_stock(self, order_setup):
        """
        Memvalidasi penolakan pesanan saat stok tidak mencukupi.

        Skenario ini memastikan bahwa transaksi akan dibatalkan jika salah satu
        produk yang diminta melebihi ketersediaan stok di gudang.
        """
        user, p1, p2 = order_setup
        items = [
            {'product_id': p1.id, 'quantity': 20},
        ]
        
        with pytest.raises(ValidationError, match="Stok produk 'Product 1' tidak mencukupi"):
            create_order(user=user, items=items)
        
        p1.refresh_from_db()
        assert p1.stock == 10

    def test_create_order_empty_items(self, order_setup):
        """
        Mencegah pembuatan pesanan tanpa adanya produk.

        Fungsi ini memastikan bahwa setiap pesanan yang masuk wajib memuat
        setidaknya satu item produk agar dianggap valid.
        """
        user, p1, p2 = order_setup
        with pytest.raises(ValidationError, match="Pesanan harus memiliki setidaknya satu produk"):
            create_order(user=user, items=[])