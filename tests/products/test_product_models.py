from django.test import TestCase
from decimal import Decimal
from products.models import Product, Category

class ProductModelTest(TestCase):
    """
    Menguji validitas integritas data model produk.

    Kelas ini memvalidasi apakah informasi katalog seperti kategori dan detail
    atribut produk dapat dikelola dengan tepat di dalam sistem.
    """

    def setUp(self):
        """
        Mempersiapkan data katalog awal untuk pengujian.

        Fungsi ini membangun relasi antara kategori dan produk contoh guna
        memastikan struktur data tersusun sebagaimana mestinya.
        """
        self.category = Category.objects.create(
            name='Anniversary Bouquet',
            description='Koleksi buket bunga romantis untuk perayaan anniversary.'
        )
        self.product = Product.objects.create(
            category=self.category,
            name='Romantic Red Rose',
            description='Buket bunga mawar merah segar dengan hiasan premium.',
            price=Decimal('250000.00'),
            stock=10
        )

    def test_product_creation(self):
        """
        Memvalidasi keakuratan atribut data produk yang tersimpan.

        Pengujian ini memastikan bahwa nilai nama, harga, serta kaitan kategori
        pada objek produk telah sesuai dengan spesifikasi katalog.
        """
        assert self.product.name == 'Romantic Red Rose'
        assert self.product.price == Decimal('250000.00')
        assert self.product.category.name == 'Anniversary Bouquet'
        assert str(self.product) == 'Romantic Red Rose'