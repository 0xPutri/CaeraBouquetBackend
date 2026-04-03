from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    """Memvalidasi data registrasi dan membuat akun pengguna baru.

    Serializer ini digunakan pada endpoint pendaftaran agar input dasar
    pengguna tervalidasi sebelum akun disimpan ke database.
    """

    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'name', 'password')

    def validate_password(self, value):
        """Memeriksa kekuatan kata sandi sesuai validator Django.

        Args:
            value (str): Kata sandi yang dikirim saat registrasi.

        Returns:
            str: Kata sandi yang telah lolos validasi.

        Raises:
            ValidationError: Jika kata sandi tidak memenuhi aturan yang berlaku.
        """
        user = User(
            email=self.initial_data.get('email', ''),
            name=self.initial_data.get('name', '')
        )

        try:
            validate_password(value, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))

        return value

    def create(self, validated_data):
        """Menyimpan akun pengguna baru berdasarkan data tervalidasi.

        Args:
            validated_data (dict): Data registrasi yang telah lolos validasi.

        Returns:
            User: Objek pengguna yang berhasil dibuat.
        """
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """Menyajikan data profil ringkas untuk pengguna yang sedang login.

    Serializer ini mengembalikan informasi identitas dasar yang aman
    ditampilkan pada endpoint profil pengguna.
    """

    class Meta:
        model = User
        fields = ('id', 'name', 'email')


class VerifiedEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Memastikan hanya pengguna dengan email terverifikasi yang dapat login.

    Serializer ini memperluas serializer JWT bawaan dengan validasi
    tambahan pada status verifikasi email pengguna.
    """

    default_error_messages = {
        'email_belum_terverifikasi': 'Email Anda belum terverifikasi.',
    }

    def validate(self, attrs):
        """Memvalidasi kredensial dan status verifikasi email pengguna.

        Args:
            attrs (dict): Data login yang berisi email dan kata sandi.

        Returns:
            dict: Payload token JWT jika autentikasi berhasil.

        Raises:
            AuthenticationFailed: Jika email pengguna belum terverifikasi.
        """
        data = super().validate(attrs)

        if not self.user.is_email_verified:
            self.fail('email_belum_terverifikasi')

        return data