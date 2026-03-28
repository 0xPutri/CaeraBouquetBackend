# CaeraBouquet Backend

Layanan ini adalah backend **REST API** untuk sistem pemesanan bouquet **Caera Bouquet**.  
Backend berperan sebagai pusat pengelolaan autentikasi pengguna, katalog produk, transaksi pesanan, dokumentasi API, dan integrasi rekomendasi berbasis machine learning.

## Ringkasan Sistem

- Framework utama: **Django** dan **Django REST Framework**.
- Fokus sistem: mendukung katalog bouquet, pemesanan pelanggan, dan pengelolaan data operasional oleh admin.
- Integrasi eksternal: layanan **Machine Learning Recommendation API** untuk rekomendasi produk.
- Dokumentasi API interaktif tersedia melalui Swagger UI.

## Fitur Utama

- Registrasi, login, dan autentikasi berbasis JWT.
- Profil pengguna yang sedang terautentikasi.
- Katalog kategori dan produk bouquet.
- Pembuatan pesanan dan riwayat pesanan pelanggan.
- Dokumentasi API berbasis **drf-spectacular**.
- Health check backend untuk kebutuhan monitoring dasar.

## Teknologi

- Python 3.13
- Django 6
- Django REST Framework
- drf-spectacular
- Simple JWT
- django-filter
- SQLite untuk pengembangan lokal

## Instalasi

1. **Clone repository**
   
   ```bash
   git clone https://github.com/0xPutri/CaeraBouquetBackend.git
   cd CaeraBouquetBackend
   ```

2. **Setup environment**
   
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. **Migrasi database**
   
   ```bash
   python manage.py migrate
   ```

4. **Jalankan aplikasi**
   
   ```bash
   python manage.py runserver
   ```

## Dokumentasi API

Dokumentasi API tidak dijelaskan ulang di README ini.  
Gunakan Swagger UI pada endpoint berikut setelah server berjalan:

- `/api/docs/` untuk dokumentasi interaktif
- `/api/schema/` untuk schema OpenAPI

## Struktur Aplikasi

- `backend/` berisi konfigurasi utama project, middleware, health check, dan exception handling.
- `users/` berisi autentikasi, profil pengguna, dan model user kustom.
- `products/` berisi kategori, katalog produk, dan integrasi rekomendasi.
- `orders/` berisi pembuatan pesanan, riwayat pesanan, dan transaksi.

## Catatan

- Backend ini dirancang untuk mendukung aplikasi web pemesanan bouquet milik **Caera Bouquet**.
- Proses pembayaran belum ditangani langsung oleh sistem.
- Integrasi rekomendasi bergantung pada layanan machine learning yang berjalan secara terpisah.

## Lisensi

Proyek ini menggunakan lisensi **MIT**. Lihat detail lengkap pada file [`LICENSE`](LICENSE).