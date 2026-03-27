from django.db import models

class Category(models.Model):
    """Menyimpan kelompok produk bouquet dalam katalog.

    Model ini membantu pengelompokan produk agar tampilan katalog lebih
    terstruktur dan mudah difilter oleh pengguna.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

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

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    external_product_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Mengembalikan nama produk sebagai representasi teks.

        Returns:
            str: Nama produk bouquet.
        """
        return self.name
