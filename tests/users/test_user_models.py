from django.test import TestCase
from django.contrib.auth import get_user_model

class UserModelTest(TestCase):
    """
    Menguji integritas model pengguna pada sistem.

    Kelas ini memastikan bahwa data pengguna seperti nama dan email
    tersimpan dengan benar di dalam database.
    """

    def setUp(self):
        """
        Menyiapkan data awal untuk kebutuhan pengujian pengguna.

        Metode ini membuat objek pengguna dummy agar dapat digunakan
        pada setiap skenario pengujian.
        """
        self.User = get_user_model()
        self.hanna_user = self.User.objects.create_user(
            email='hanna@caerabouquet.com',
            name='Hanna Fernanda',
            password='Password123!'
        )

    def test_user_creation(self):
        """
        Memvalidasi keberhasilan pembuatan akun pengguna baru.

        Memastikan atribut nama, email, dan kata sandi sesuai dengan
        data yang didaftarkan.
        """
        user = self.hanna_user
        assert user.name == 'Hanna Fernanda'
        assert user.email == 'hanna@caerabouquet.com'
        assert user.check_password('Password123!')
        assert str(user) == 'hanna@caerabouquet.com'