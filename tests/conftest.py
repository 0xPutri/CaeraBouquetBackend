"""
Mengatur konfigurasi global untuk seluruh rangkaian pengujian.

File ini berfungsi sebagai titik awal inisialisasi Django agar lingkungan
pengujian siap digunakan oleh pytest.
"""

import os
import django
from django.conf import settings


def pytest_configure():
    """
    Menyiapkan lingkungan Django sebelum pengujian dijalankan.

    Mengatur variabel lingkungan yang diperlukan dan memanggil fungsi
    setup untuk menginisialisasi aplikasi.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.dev')
    os.environ.setdefault('SECRET_KEY', 'test-secret-key-123')
    django.setup()