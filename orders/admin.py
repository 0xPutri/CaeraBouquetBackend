import logging
from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.db import transaction
from .models import Order, Transaction
from products.models import Product
from .services import snapshot_order_transactions, sync_order_inventory

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
            'total_price': 'Total nilai pesanan dihitung otomatis dari detail transaksi.',
            'status': 'Status proses pesanan.',
            'delivery_address': 'Alamat pengiriman pesanan.',
            'notes': 'Catatan tambahan untuk pesanan.',
        }


class TransactionInlineFormSet(forms.BaseInlineFormSet):
    """Memvalidasi perubahan transaksi admin sebelum disimpan.

    Formset ini menjaga agar perubahan transaksi di admin tetap aman
    dengan memeriksa kebutuhan stok sebelum sinkronisasi dijalankan.
    """

    def clean(self):
        """Memeriksa kecukupan stok dari perubahan transaksi admin.

        Fungsi ini menghitung selisih jumlah transaksi lama dan baru
        agar admin tidak dapat menyimpan transaksi melebihi stok.

        Raises:
            ValidationError: Jika stok produk tidak mencukupi.
        """
        super().clean()
        if any(self.errors):
            return

        previous_snapshot = snapshot_order_transactions(self.instance)
        current_quantity_by_product = {}
        previous_quantity_by_product = {}

        for previous_item in previous_snapshot.values():
            if previous_item['product_id'] is None:
                continue
            previous_quantity_by_product[previous_item['product_id']] = (
                previous_quantity_by_product.get(previous_item['product_id'], 0) + previous_item['quantity']
            )

        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue

            product = cleaned_data.get('product')
            quantity = cleaned_data.get('quantity')
            if product is None or quantity is None:
                continue

            current_quantity_by_product[product.id] = current_quantity_by_product.get(product.id, 0) + quantity

        products = Product.objects.in_bulk(current_quantity_by_product.keys())

        for product_id, current_quantity in current_quantity_by_product.items():
            stock_delta = current_quantity - previous_quantity_by_product.get(product_id, 0)
            if stock_delta > 0 and products[product_id].stock < stock_delta:
                audit_logger.warning(
                    "Validasi transaksi admin gagal karena stok tidak mencukupi.",
                    extra={"order_id": self.instance.id, "product_id": product_id, "required_stock": stock_delta}
                )
                raise forms.ValidationError("Stok tidak mencukupi untuk transaksi admin yang dimasukkan.")

class TransactionInline(TabularInline):
    """Menampilkan detail transaksi langsung di halaman pesanan.

    Inline ini membantu admin melihat item produk yang terkait dengan
    suatu pesanan tanpa berpindah halaman.
    """

    form = TransactionInlineForm
    formset = TransactionInlineFormSet
    model = Transaction
    extra = 1
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    """Mengatur tampilan data pesanan pada Django Admin.

    Konfigurasi ini memudahkan admin memantau status, total harga,
    identitas pengguna, dan detail transaksi dari setiap pesanan.
    """

    form = OrderAdminForm
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__name')
    inlines = [TransactionInline]
    readonly_fields = ('total_price',)

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

    def save_related(self, request, form, formsets, change):
        """Menyimpan transaksi inline lalu menyelaraskan data pesanan.

        Fungsi ini memastikan perubahan admin pada detail transaksi
        tetap konsisten dengan stok produk dan total order.

        Args:
            request (HttpRequest): Request admin yang sedang diproses.
            form (ModelForm): Form utama order yang telah divalidasi.
            formsets (list): Kumpulan inline formset yang ikut disimpan.
            change (bool): Penanda apakah order sedang diubah.

        Returns:
            None: Method ini tidak mengembalikan nilai.

        Raises:
            ValidationError: Jika sinkronisasi stok gagal dipenuhi.
        """
        previous_snapshot = snapshot_order_transactions(form.instance)
        with transaction.atomic():
            super().save_related(request, form, formsets, change)
            sync_order_inventory(form.instance, previous_snapshot)
        audit_logger.warning(
            "Admin menyimpan detail transaksi pesanan.",
            extra={"admin_user": str(request.user.id), "order_id": form.instance.id, "status": form.instance.status}
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