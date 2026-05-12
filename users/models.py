import uuid
import logging

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.db import models

logger = logging.getLogger('users')


class UserManager(BaseUserManager):
    """Mengelola proses pembuatan akun pengguna.

    Manager ini menyediakan alur pembuatan pengguna biasa dan superuser
    dengan validasi email dasar yang dibutuhkan sistem autentikasi.
    """

    def create_user(self, email, name, password=None, **extra_fields):
        """Membuat akun pengguna baru dengan email sebagai identitas utama.

        Args:
            email (str): Alamat email yang akan digunakan untuk login.
            name (str): Nama pengguna yang disimpan pada profil akun.
            password (str | None): Kata sandi awal untuk akun pengguna.
            **extra_fields: Field tambahan yang ingin disimpan ke model.

        Returns:
            User: Objek pengguna yang sudah tersimpan di database.

        Raises:
            ValueError: Jika email tidak diberikan saat pembuatan akun.
        """
        if not email:
            raise ValueError("Email wajib diisi")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        """Membuat akun superuser dengan hak akses administratif.

        Args:
            email (str): Alamat email untuk akun administrator.
            name (str): Nama administrator yang akan disimpan.
            password (str | None): Kata sandi untuk akun administrator.
            **extra_fields: Field tambahan yang diteruskan ke model pengguna.

        Returns:
            User: Objek superuser yang sudah tersimpan di database.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Merepresentasikan akun pengguna pada sistem Caera Bouquet.

    Model ini menyimpan identitas dasar pengguna, status akses, dan
    informasi verifikasi email untuk kebutuhan autentikasi aplikasi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID Pengguna")
    email = models.EmailField(unique=True, verbose_name="Alamat Email")
    name = models.CharField(max_length=255, verbose_name="Nama Lengkap")

    is_active = models.BooleanField(default=True, verbose_name="Akun Aktif")
    is_staff = models.BooleanField(default=False, verbose_name="Akses Staff Admin")

    is_email_verified = models.BooleanField(default=False, verbose_name="Email Terverifikasi")
    email_verification_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token Verifikasi")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tanggal Mendaftar")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = "Data Pengguna"
        verbose_name_plural = "Data Pengguna"

    def __str__(self):
        """Mengembalikan representasi teks dari pengguna.

        Returns:
            str: Nilai email pengguna.
        """
        return self.email
    
    def send_verification_email(self):
        """Mengirim email verifikasi ke alamat email pengguna.

        Method ini memastikan token verifikasi tersedia, lalu mengirimkan
        tautan verifikasi email menggunakan konfigurasi SMTP aplikasi.
        """
        if not self.email_verification_token:
            self.email_verification_token = uuid.uuid4().hex
            self.save(update_fields=['email_verification_token'])

        verification_url = (
            f"{settings.EMAIL_VERIFICATION_BASE_URL}"
            f"?token={self.email_verification_token}"
        )
        subject = "Verifikasi Email Akun Caera Bouquet"
        message = (
            f"Halo {self.name},\n\n"
            "Terima kasih telah mendaftar di Caera Bouquet.\n"
            "Untuk melanjutkan proses pendaftaran, silakan lakukan verifikasi email Anda melalui tautan berikut:\n\n"
            f"{verification_url}\n\n"
            "Tautan ini bersifat pribadi dan hanya berlaku untuk Anda.\n\n"
            "Jika Anda tidak merasa melakukan pendaftaran akun, silakan abaikan email ini.\n\n"
            "Salam hangat,\n"
            "Tim Caera Bouquet"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            fail_silently=False,
        )

        logger.info(
            "Email verifikasi berhasil dikirim.",
            extra={"user_id": str(self.id), "email": self.email}
        )

    def send_password_reset_email(self):
        """
        Mengirim tautan atur ulang kata sandi ke email pengguna.

        Fungsi ini menghasilkan token yang aman dan memuatnya ke dalam
        tautan yang akan dikirim ke pengguna.
        """
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self)
        uid = urlsafe_base64_encode(force_bytes(self.pk))

        reset_url = (
            f"{settings.PASSWORD_RESET_BASE_URL}"
            f"?uid={uid}&token={token}"
        )
        subject = "Atur Ulang Kata Sandi Akun Caera Bouquet"
        message = (
            f"Halo {self.name},\n\n"
            "Kami menerima permintaan untuk mengatur ulang kata sandi akun Anda.\n"
            "Silakan klik tautan berikut untuk membuat kata sandi baru:\n\n"
            f"{reset_url}\n\n"
            "Tautan ini hanya berlaku sementara untuk alasan keamanan.\n"
            "Jika Anda tidak meminta pengaturan ulang kata sandi, abaikan email ini.\n\n"
            "Salam hangat,\n"
            "Tim Caera Bouquet"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            fail_silently=False,
        )

        logger.info(
            "Email atur ulang kata sandi berhasil dikirim.",
            extra={"user_id": str(self.id), "email": self.email}
        )


class CustomGroup(Group):
    """
    Representasi grup otorisasi untuk pengaturan izin akses.

    Model proxy ini digunakan untuk mengelola peran pengguna dalam sistem
    agar penamaan dan pengelompokannya lebih mudah dipahami oleh administrator.
    """
    class Meta:
        proxy = True
        verbose_name = "Grup Otorisasi"
        verbose_name_plural = "Daftar Grup Otorisasi"
        app_label = 'users'