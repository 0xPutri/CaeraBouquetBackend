from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Menyimpan konfigurasi aplikasi pengguna.

    Kelas ini membantu Django mengenali app `users` saat proses inisialisasi.
    """

    name = 'users'