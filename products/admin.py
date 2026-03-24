from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Mengatur tampilan kategori produk pada Django Admin.

    Konfigurasi ini menampilkan field penting agar admin lebih mudah
    mencari dan meninjau data kategori katalog.
    """

    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Mengatur tampilan produk pada Django Admin.

    Konfigurasi ini membantu admin memantau kategori, harga, stok, dan
    data pencarian produk secara lebih efisien.
    """

    list_display = ('name', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')