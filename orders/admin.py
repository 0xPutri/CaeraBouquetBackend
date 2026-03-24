from django.contrib import admin
from .models import Order, Transaction

class TransactionInline(admin.TabularInline):
    """Menampilkan detail transaksi langsung di halaman pesanan.

    Inline ini membantu admin melihat item produk yang terkait dengan
    suatu pesanan tanpa berpindah halaman.
    """

    model = Transaction
    extra = 0
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Mengatur tampilan data pesanan pada Django Admin.

    Konfigurasi ini memudahkan admin memantau status, total harga,
    identitas pengguna, dan detail transaksi dari setiap pesanan.
    """

    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__name')
    inlines = [TransactionInline]