from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from .models import User, CustomGroup

admin.site.unregister(Group)

class UserAdminForm(forms.ModelForm):
    """Menyediakan bantuan isian untuk form pengguna di Django Admin.

    Form ini menambahkan penjelasan singkat agar admin lebih mudah
    memahami tujuan setiap field saat mengelola akun pengguna.
    """

    class Meta:
        model = User
        fields = '__all__'
        help_texts = {
            'email_verification_token': 'Kosongkan jika token tidak digunakan.',
            'is_email_verified': 'Tandai jika email sudah terverifikasi.',
            'email': 'Email ini digunakan untuk login.',
            'name': 'Nama yang tampil pada profil dan pesanan.',
            'is_active': 'Nonaktifkan jika akun tidak boleh masuk.',
            'is_staff': 'Izinkan akun mengakses Django Admin.',
            'is_superuser': 'Berikan akses penuh ke seluruh sistem.',
            'groups': 'Gunakan untuk pengelompokan izin.',
            'user_permissions': 'Gunakan untuk izin khusus tambahan.',
        }

@admin.register(User)
class UserAdmin(ModelAdmin):
    """Mengatur tampilan data pengguna pada Django Admin.

    Konfigurasi ini memudahkan admin melihat identitas, status akses,
    dan informasi verifikasi email dari setiap akun.
    """

    form = UserAdminForm
    list_display = ('email', 'name', 'is_staff', 'is_email_verified', 'created_at')
    search_fields = ('email', 'name')
    list_filter = ('is_staff', 'is_email_verified', 'is_active')
    readonly_fields = ('password',)
    filter_horizontal = ('groups', 'user_permissions')

@admin.register(CustomGroup)
class CustomGroupAdmin(ModelAdmin):
    """
    Mengatur pengelompokan hak akses dan peran pengguna.

    Kelas ini memungkinkan administrator untuk mendefinisikan grup otorisasi agar
    pemberian izin akses fitur aplikasi menjadi lebih terstruktur.
    """
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)