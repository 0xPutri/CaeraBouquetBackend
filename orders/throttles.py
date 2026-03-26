from rest_framework.throttling import UserRateThrottle


class OrderCreateUserRateThrottle(UserRateThrottle):
    """Membatasi frekuensi pembuatan pesanan per pengguna."""

    scope = 'order_create'