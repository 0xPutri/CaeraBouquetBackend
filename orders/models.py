from django.db import models
from django.conf import settings
from products.models import Product

class Order(models.Model):
    """Menyimpan data utama pesanan yang dibuat pengguna.

    Model ini merekam pemilik pesanan, nilai total, status proses,
    alamat pengiriman, serta catatan tambahan dari pelanggan.
    """

    STATUS_CHOICES = [
        ('created', 'Dibuat'),
        ('processing', 'Diproses'),
        ('completed', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    delivery_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Mengembalikan identitas ringkas dari pesanan.

        Returns:
            str: Teks yang memuat nomor pesanan dan nama pengguna.
        """
        return f"Order #{self.id} - {self.user.name}"
    
class Transaction(models.Model):
    """Menyimpan detail item produk pada sebuah pesanan.

    Model ini menghubungkan pesanan dengan produk yang dibeli, jumlah
    item, serta harga yang dicatat saat transaksi dibuat.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions', verbose_name="Nomor Pesanan")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Nama Produk")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Jumlah (Qty)")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Harga Satuan")

    class Meta:
        verbose_name = "Detail Transaksi"
        verbose_name_plural = "Detail Transaksi"

    def save(self, *args, **kwargs):
        """Menyimpan transaksi dan mengisi harga dari produk bila perlu.

        Args:
            *args: Argumen tambahan untuk method `save`.
            **kwargs: Argumen keyword tambahan untuk method `save`.

        Returns:
            None: Method ini tidak mengembalikan nilai.
        """
        if not self.price and self.product:
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        """Mengembalikan representasi teks dari detail transaksi.

        Returns:
            str: Teks yang memuat jumlah produk dan identitas pesanan.
        """
        product_name = self.product.name if self.product else "Produk Dihapus"
        return f"{self.quantity}x {product_name} (Order #{self.order.id})"