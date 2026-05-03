import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_account(db):
    """
    Menyiapkan akun pengguna standar untuk pengujian.

    Fungsi ini membuat data profil lengkap yang sudah terverifikasi guna
    mensimulasikan skenario login dan akses profil yang sah.
    """
    return User.objects.create_user(
        email='hanna@caerabouquet.com',
        name='Hanna Fernanda',
        password='SafePassword123!',
        is_email_verified=True
    )

@pytest.mark.django_db
class TestUserAPI:
    """
    Menguji alur keamanan dan manajemen profil pengguna.

    Kelas ini memvalidasi proses autentikasi serta memastikan hak akses
    terhadap data pribadi pengguna terlindungi dengan ketat.
    """

    def test_user_login_success(self, api_client, user_account):
        """
        Memastikan kredensial yang tepat mampu menghasilkan token akses.

        Skenario ini menguji apakah sistem berhasil memberikan token JWT yang
        valid bagi pengguna yang memasukkan email dan kata sandi yang benar.
        """
        url = reverse('login')
        data = {
            'email': 'hanna@caerabouquet.com',
            'password': 'SafePassword123!'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_get_profile_unauthorized(self, api_client):
        """
        Memvalidasi perlindungan privasi bagi pengguna yang belum login.

        Pengujian ini memastikan bahwa akses terhadap data profil akan ditolak
        secara otomatis jika permintaan tidak menyertakan bukti autentikasi.
        """
        url = reverse('user_profile')
        response = api_client.get(url)
        
        assert response.status_code == 401

    def test_get_profile_authorized(self, api_client, user_account):
        """
        Memastikan ketersediaan data profil bagi pengguna yang sah.

        Fungsi ini memverifikasi bahwa pengguna yang telah berhasil masuk dapat
        mengambil informasi akun mereka secara lengkap dan akurat.
        """
        api_client.force_authenticate(user=user_account)
        url = reverse('user_profile')
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert response.data['email'] == 'hanna@caerabouquet.com'
        assert response.data['name'] == 'Hanna Fernanda'