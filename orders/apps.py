from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Menyimpan konfigurasi aplikasi pesanan.

    Kelas ini membantu Django mengenali app `orders` saat aplikasi dimuat.
    """

    name = 'orders'