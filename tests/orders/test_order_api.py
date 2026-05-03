import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from products.models import Product, Category
from orders.models import Order

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_user(db, api_client):
    user = User.objects.create_user(
        email='buyer@caerabouquet.com',
        name='Buyer',
        password='Password123!'
    )
    api_client.force_authenticate(user=user)
    return user

@pytest.fixture
def products(db):
    category = Category.objects.create(name='Katalog')
    p1 = Product.objects.create(category=category, name='Bunga A', price=Decimal('50000.00'), stock=10)
    p2 = Product.objects.create(category=category, name='Bunga B', price=Decimal('75000.00'), stock=5)
    return p1, p2

@pytest.mark.django_db
class TestOrderAPI:
    """
    Menguji fungsionalitas endpoint API pesanan.

    Kelas ini memastikan bahwa proses pembuatan dan pengambilan data pesanan
    melalui jalur HTTP berjalan sesuai dengan spesifikasi sistem.
    """

    def test_post_order_multi_items(self, api_client, authenticated_user, products):
        """
        Memastikan pembuatan pesanan banyak produk via API berhasil.

        Fungsi ini menguji apakah endpoint mampu menerima daftar item produk
        dan membentuk transaksi yang sah di dalam database.
        """
        p1, p2 = products
        url = reverse('order-list-create')
        data = {
            'items': [
                {'product_id': p1.id, 'quantity': 2},
                {'product_id': p2.id, 'quantity': 1}
            ],
            'delivery_address': 'Alamat Baru'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == 201
        assert 'order_id' in response.data
        
        # Verifikasi database
        order = Order.objects.get(id=response.data['order_id'])
        assert order.transactions.count() == 2
        assert order.total_price == Decimal('175000.00')

    def test_post_order_legacy_format(self, api_client, authenticated_user, products):
        """
        Menjamin dukungan format pesanan tunggal tetap tersedia.

        Pengujian ini memverifikasi bahwa sistem masih kompatibel dengan cara lama
        dalam mengirimkan data pesanan untuk satu jenis produk saja.
        """
        p1, _ = products
        url = reverse('order-list-create')
        data = {
            'product_id': p1.id,
            'quantity': 1,
            'delivery_address': 'Alamat Legacy'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == 201
        order = Order.objects.get(id=response.data['order_id'])
        assert order.transactions.count() == 1
        assert order.total_price == Decimal('50000.00')

    def test_get_order_history_structure(self, api_client, authenticated_user, products):
        """
        Memvalidasi kelengkapan struktur data riwayat pesanan.

        Skenario ini memastikan bahwa respons dari server memuat rincian item,
        harga total, serta informasi pendukung lainnya secara mendetail.
        """
        p1, p2 = products
        # Buat satu order dulu
        url_post = reverse('order-list-create')
        api_client.post(url_post, {
            'items': [{'product_id': p1.id, 'quantity': 1}],
            'delivery_address': 'Test'
        }, format='json')

        url_get = reverse('order-list-create') # Same as list url
        response = api_client.get(url_get)
        
        assert response.status_code == 200
        # Cek struktur respons
        first_order = response.data['results'][0]
        assert 'items' in first_order
        assert 'total_price' in first_order
        assert len(first_order['items']) == 1
        assert first_order['items'][0]['product_name'] == 'Bunga A'
