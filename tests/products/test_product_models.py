from django.test import TestCase
from decimal import Decimal
from products.models import Product, Category

class ProductModelTest(TestCase):
    """
    Menguji validitas model produk bouquet.

    Kelas ini memeriksa apakah kategori dan detail produk dapat
    dikelola dengan tepat dalam katalog.
    """

    def setUp(self):
        """
        Menyiapkan contoh produk dan kategori untuk diuji.

        Langkah ini memastikan tersedianya kategori Anniversary dan
        produk mawar merah sebagai data dummy.
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
        Memastikan detail produk tersimpan dengan akurat.

        Memeriksa kesesuaian nama, harga, dan relasi kategori pada
        objek produk yang dibuat.
        """
        assert self.product.name == 'Romantic Red Rose'
        assert self.product.price == Decimal('250000.00')
        assert self.product.category.name == 'Anniversary Bouquet'
        assert str(self.product) == 'Romantic Red Rose'