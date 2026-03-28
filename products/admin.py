import logging
from django import forms
from django.contrib import admin
from .models import Category, Product

audit_logger = logging.getLogger('caera.security')

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
            'external_product_id': 'ID produk eksternal untuk sinkronisasi dengan layanan ML (contoh: B001).',
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

    def save_model(self, request, obj, form, change):
        """Menyimpan kategori dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Category): Objek kategori yang akan disimpan.
            form (ModelForm): Form admin yang memuat data kategori.
            change (bool): Penanda apakah data sedang diubah.
        """
        super().save_model(request, obj, form, change)
        action = 'perubahan' if change else 'penambahan'
        audit_logger.warning(
            "Admin melakukan %s kategori.",
            action,
            extra={"admin_user": str(request.user.id), "category_id": obj.id, "category_name": obj.name}
        )

    def delete_model(self, request, obj):
        """Menghapus kategori dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Category): Objek kategori yang akan dihapus.
        """
        audit_logger.warning(
            "Admin menghapus kategori.",
            extra={"admin_user": str(request.user.id), "category_id": obj.id, "category_name": obj.name}
        )
        super().delete_model(request, obj)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Mengatur tampilan produk pada Django Admin.

    Konfigurasi ini membantu admin memantau kategori, harga, stok, dan
    data pencarian produk secara lebih efisien.
    """

    form = ProductAdminForm
    list_display = ('external_product_id', 'name', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category',)
    search_fields = ('external_product_id', 'name', 'category__name')

    def save_model(self, request, obj, form, change):
        """Menyimpan produk dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Product): Objek produk yang akan disimpan.
            form (ModelForm): Form admin yang memuat data produk.
            change (bool): Penanda apakah data sedang diubah.
        """
        super().save_model(request, obj, form, change)
        action = 'perubahan' if change else 'penambahan'
        audit_logger.warning(
            "Admin melakukan %s produk.",
            action,
            extra={
                "admin_user": str(request.user.id),
                "product_id": obj.id,
                "external_product_id": obj.external_product_id,
                "product_name": obj.name
            }
        )

    def delete_model(self, request, obj):
        """Menghapus produk dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Product): Objek produk yang akan dihapus.
        """
        audit_logger.warning(
            "Admin menghapus produk.",
            extra={
                "admin_user": str(request.user.id),
                "product_id": obj.id,
                "external_product_id": obj.external_product_id,
                "product_name": obj.name
            }
        )
        super().delete_model(request, obj)