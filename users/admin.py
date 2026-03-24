from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Mengatur tampilan data pengguna pada Django Admin.

    Konfigurasi ini memudahkan admin melihat identitas, status akses,
    dan informasi verifikasi email dari setiap akun.
    """

    list_display = ('email', 'name', 'is_staff', 'is_email_verified', 'created_at')
    search_fields = ('email', 'name')
    list_filter = ('is_staff', 'is_email_verified', 'is_active')
    readonly_fields = ('password',)