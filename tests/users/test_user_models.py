from django.test import TestCase
from django.contrib.auth import get_user_model

class UserModelTest(TestCase):
    """
    Menguji validitas integritas data pada model pengguna.

    Kelas ini memastikan bahwa informasi identitas inti pengguna mampu
    tercatat dan tersimpan dengan presisi di dalam database.
    """

    def setUp(self):
        """
        Mempersiapkan data identitas awal untuk pengujian.

        Fungsi ini membangun objek pengguna contoh guna memastikan fondasi
        autentikasi dapat diuji secara menyeluruh.
        """
        self.User = get_user_model()
        self.hanna_user = self.User.objects.create_user(
            email='hanna@caerabouquet.com',
            name='Hanna Fernanda',
            password='Password123!'
        )

    def test_user_creation(self):
        """
        Memvalidasi presisi penyimpanan data pendaftaran akun.

        Pengujian ini memastikan bahwa atribut nama, email, serta status keamanan
        pengguna telah sesuai dengan informasi yang didaftarkan.
        """
        user = self.hanna_user
        assert user.name == 'Hanna Fernanda'
        assert user.email == 'hanna@caerabouquet.com'
        assert user.check_password('Password123!')
        assert str(user) == 'hanna@caerabouquet.com'