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
        exclude = ('groups', 'user_permissions', 'password')
        help_texts = {
            'email_verification_token': 'Kosongkan jika token tidak digunakan.',
            'is_email_verified': 'Tandai jika email sudah terverifikasi.',
            'email': 'Email ini digunakan untuk login.',
            'name': 'Nama yang tampil pada profil dan pesanan.',
            'is_active': 'Nonaktifkan jika akun tidak boleh masuk.',
            'is_staff': 'Izinkan akun mengakses Django Admin.',
            'is_superuser': 'Berikan akses penuh ke seluruh sistem.',
        }


@admin.register(User)
class UserAdmin(ModelAdmin):
    """Mengatur tampilan data pengguna pada Django Admin.

    Konfigurasi ini memudahkan admin melihat identitas, status akses,
    dan informasi verifikasi email dari setiap akun.
    """

    form = UserAdminForm
    exclude = ('groups', 'user_permissions', 'password')
    list_display = ('email', 'name', 'is_staff', 'is_email_verified', 'created_at')
    search_fields = ('email', 'name')
    list_filter = ('is_staff', 'is_email_verified', 'is_active')
    readonly_fields = ('obscured_password',)

    def obscured_password(self, obj):
        """
        Menyensor tampilan kata sandi pada antarmuka admin.

        Fungsi ini mengganti hash kata sandi asli dengan teks penutup untuk
        melindungi privasi pengguna dan mencegah kebocoran data.

        Args:
            obj (User): Objek pengguna yang sedang ditampilkan.

        Returns:
            str: Teks statis yang menginformasikan bahwa sandi disembunyikan.
        """
        return "********"

    obscured_password.short_description = 'Kata Sandi'


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