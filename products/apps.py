from django.apps import AppConfig


class ProductsConfig(AppConfig):
    """Menyimpan konfigurasi aplikasi katalog produk.

    Kelas ini digunakan Django untuk mendaftarkan app `products`.
    """

    name = 'products'
    verbose_name = 'Katalog Produk'