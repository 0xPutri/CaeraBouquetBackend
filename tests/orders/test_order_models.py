from django.test import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model
from products.models import Product, Category
from orders.models import Order, Transaction

class OrderModelTest(TestCase):
    """
    Menguji fungsionalitas model pesanan dan transaksi.

    Kelas ini memvalidasi hubungan antara pelanggan, produk yang
    dipesan, serta rincian transaksi yang terbentuk.
    """

    def setUp(self):
        """
        Mempersiapkan data awal untuk pengujian model.

        Fungsi ini membangun fondasi data seperti pengguna dan produk agar
        proses simulasi pembuatan pesanan dapat berjalan dengan valid.
        """
        User = get_user_model()
        self.user = User.objects.create_user(
            email='hanna@caerabouquet.com',
            name='Hanna Fernanda',
            password='Password123!'
        )
        self.category = Category.objects.create(name='Wedding Bouquet')
        self.product = Product.objects.create(
            category=self.category,
            name='Elegant White Lily',
            description='Buket lily putih elegan untuk pernikahan.',
            price=Decimal('350000.00'),
            stock=5
        )

    def test_order_and_transaction_creation(self):
        """
        Memvalidasi keterkaitan antara pesanan dan rincian transaksi.

        Pengujian ini memastikan bahwa data pesanan yang dibuat tersimpan
        dengan benar beserta item produk yang menyertainya.
        """
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('350000.00'),
            delivery_address='Jl. Kenanga No. 12, Jakarta Selatan'
        )
        transaction = Transaction.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        assert order.user.name == 'Hanna Fernanda'
        assert order.status == 'created'
        assert transaction.product.name == 'Elegant White Lily'
        assert order.transactions.count() == 1
        assert str(order).startswith(f"Order #{order.id}")