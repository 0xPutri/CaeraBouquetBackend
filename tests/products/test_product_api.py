import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from products.models import Product, Category

@pytest.fixture
def api_client():
    """Menyediakan klien API untuk simulasi request."""
    return APIClient()

@pytest.fixture
def product_data(db):
    """
    Menyiapkan data kategori dan produk contoh.

    Fungsi ini mengisi database sementara dengan data katalog dasar untuk
    mendukung pengujian fitur daftar dan filter produk.
    """
    cat = Category.objects.create(name='Bunga Meja')
    Product.objects.create(
        category=cat,
        name='Mawar Merah',
        price=Decimal('50000.00'),
        stock=10
    )
    return cat

@pytest.mark.django_db
class TestProductAPI:
    """
    Menguji aksesibilitas data pada katalog produk.

    Kelas ini memverifikasi bahwa informasi produk dan kategori dapat
    dikonsumsi secara publik dengan struktur data yang konsisten.
    """

    def test_get_categories_list(self, api_client, product_data):
        """
        Memastikan daftar kategori dapat diakses dengan benar.

        Pengujian ini memvalidasi apakah endpoint mampu menyajikan seluruh
        kategori produk yang tersedia secara publik.
        """
        url = reverse('category-list')
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert response.data['count'] >= 1
        assert response.data['results'][0]['name'] == 'Bunga Meja'

    def test_get_products_list(self, api_client, product_data):
        """
        Memastikan ketersediaan informasi produk pada katalog.

        Fungsi ini memeriksa apakah data produk tampil secara akurat saat
        diakses melalui endpoint daftar produk utama.
        """
        url = reverse('product-list')
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert response.data['count'] >= 1
        assert response.data['results'][0]['name'] == 'Mawar Merah'

    def test_filter_products_by_category(self, api_client, product_data):
        """
        Memvalidasi keakuratan fitur penyaringan kategori.

        Skenario ini menguji apakah sistem mampu menampilkan produk yang
        relevan sesuai dengan kategori yang dipilih oleh pengguna.
        """
        url = reverse('product-list')
        response = api_client.get(url, {'category': product_data.id})
        
        assert response.status_code == 200
        assert response.data['count'] == 1
