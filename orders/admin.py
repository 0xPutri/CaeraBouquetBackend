import logging
from django import forms
from django.contrib import admin
from .models import Order, Transaction

audit_logger = logging.getLogger('caera.security')

class TransactionInlineForm(forms.ModelForm):
    """Menyediakan bantuan isian untuk detail item transaksi.

    Form ini membantu admin memahami data produk, jumlah, dan harga
    yang tercatat pada setiap pesanan.
    """

    class Meta:
        model = Transaction
        fields = '__all__'
        help_texts = {
            'product': 'Pilih produk pada transaksi ini.',
            'quantity': 'Jumlah item yang dipesan.',
            'price': 'Harga per item saat transaksi dibuat.',
        }


class OrderAdminForm(forms.ModelForm):
    """Menyediakan bantuan isian untuk pengelolaan pesanan di admin.

    Form ini memberi konteks operasional agar admin lebih mudah
    memantau status dan informasi pengiriman pesanan pelanggan.
    """

    class Meta:
        model = Order
        fields = '__all__'
        help_texts = {
            'user': 'Pelanggan pemilik pesanan ini.',
            'total_price': 'Total nilai pesanan.',
            'status': 'Status proses pesanan.',
            'delivery_address': 'Alamat pengiriman pesanan.',
            'notes': 'Catatan tambahan untuk pesanan.',
        }

class TransactionInline(admin.TabularInline):
    """Menampilkan detail transaksi langsung di halaman pesanan.

    Inline ini membantu admin melihat item produk yang terkait dengan
    suatu pesanan tanpa berpindah halaman.
    """

    form = TransactionInlineForm
    model = Transaction
    extra = 1
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Mengatur tampilan data pesanan pada Django Admin.

    Konfigurasi ini memudahkan admin memantau status, total harga,
    identitas pengguna, dan detail transaksi dari setiap pesanan.
    """

    form = OrderAdminForm
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__name')
    inlines = [TransactionInline]

    def save_model(self, request, obj, form, change):
        """Menyimpan pesanan dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Order): Objek pesanan yang akan disimpan.
            form (ModelForm): Form admin yang memuat data pesanan.
            change (bool): Penanda apakah data sedang diubah.
        """
        super().save_model(request, obj, form, change)
        action = 'perubahan' if change else 'penambahan'
        audit_logger.warning(
            "Admin melakukan %s pesanan.",
            action,
            extra={"admin_user": str(request.user.id), "order_id": obj.id, "status": obj.status}
        )

    def delete_model(self, request, obj):
        """Menghapus pesanan dan mencatat aktivitas admin.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            obj (Order): Objek pesanan yang akan dihapus.
        """
        audit_logger.warning(
            "Admin menghapus pesanan.",
            extra={"admin_user": str(request.user.id), "order_id": obj.id, "status": obj.status}
        )
        super().delete_model(request, obj)