from django.db import models


class Category(models.Model):
    """Menyimpan kelompok produk bouquet dalam katalog.

    Model ini membantu pengelompokan produk agar tampilan katalog lebih
    terstruktur dan mudah difilter oleh pengguna.
    """

    name = models.CharField(max_length=100, verbose_name="Nama Kategori")
    description = models.TextField(blank=True, null=True, verbose_name="Deskripsi Kategori")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")

    class Meta:
        verbose_name = "Kategori Produk"
        verbose_name_plural = "Kategori Produk"
        ordering = ['-created_at']

    def __str__(self):
        """Mengembalikan nama kategori sebagai representasi teks.

        Returns:
            str: Nama kategori produk.
        """
        return self.name


class Product(models.Model):
    """Menyimpan informasi utama dari produk bouquet.

    Model ini memuat relasi kategori, detail harga, stok, deskripsi,
    serta gambar yang akan ditampilkan pada katalog produk.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Kategori Utama")
    external_product_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="ID Produk Eksternal")
    name = models.CharField(max_length=255, verbose_name="Nama Produk")
    description = models.TextField(verbose_name="Deskripsi Lengkap")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Harga (Rp)")
    stock = models.PositiveIntegerField(default=0, verbose_name="Jumlah Stok")
    image_url = models.URLField(blank=True, null=True, verbose_name="URL Gambar/Foto")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Didaftarkan Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Terakhir Diperbarui")

    class Meta:
        verbose_name = "Produk Bouquet"
        verbose_name_plural = "Daftar Produk"
        ordering = ['-created_at']

    def __str__(self):
        """Mengembalikan nama produk sebagai representasi teks.

        Returns:
            str: Nama produk bouquet.
        """
        return self.name