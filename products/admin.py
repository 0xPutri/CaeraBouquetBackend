from django import forms
from django.contrib import admin
from .models import Category, Product


class CategoryAdminForm(forms.ModelForm):
    """Menyediakan bantuan isian untuk pengelolaan kategori produk.

    Form ini membantu admin menjaga konsistensi nama dan deskripsi
    kategori agar katalog lebih rapi dan mudah dipahami pelanggan.
    """

    class Meta:
        model = Category
        fields = '__all__'
        help_texts = {
            'name': 'Nama kategori yang tampil di katalog.',
            'description': 'Penjelasan singkat tentang kategori ini.',
        }


class ProductAdminForm(forms.ModelForm):
    """Menyediakan bantuan isian untuk pengelolaan data produk.

    Form ini menambahkan keterangan operasional agar admin dapat
    mengisi informasi katalog secara konsisten dan akurat.
    """

    class Meta:
        model = Product
        fields = '__all__'
        help_texts = {
            'category': 'Pilih kategori produk.',
            'name': 'Nama produk yang tampil di katalog.',
            'description': 'Deskripsi singkat produk.',
            'price': 'Harga jual produk.',
            'stock': 'Jumlah stok yang tersedia.',
            'image_url': 'URL gambar produk.',
        }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Mengatur tampilan kategori produk pada Django Admin.

    Konfigurasi ini menampilkan field penting agar admin lebih mudah
    mencari dan meninjau data kategori katalog.
    """

    form = CategoryAdminForm
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Mengatur tampilan produk pada Django Admin.

    Konfigurasi ini membantu admin memantau kategori, harga, stok, dan
    data pencarian produk secara lebih efisien.
    """

    form = ProductAdminForm
    list_display = ('name', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')