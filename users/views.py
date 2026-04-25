import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, inline_serializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import RegisterSerializer, UserProfileSerializer, VerifiedEmailTokenObtainPairSerializer

User = get_user_model()

logger = logging.getLogger('users')
security_logger = logging.getLogger('caera.security')

register_success_response = inline_serializer(
    name='RegisterSuccessResponse',
    fields={
        'message': serializers.CharField(help_text='Pesan sukses setelah registrasi berhasil.'),
    },
)

token_pair_request = inline_serializer(
    name='TokenPairRequest',
    fields={
        'email': serializers.EmailField(help_text='Alamat email pengguna yang terdaftar.'),
        'password': serializers.CharField(help_text='Kata sandi akun pengguna.'),
    },
)

token_refresh_request = inline_serializer(
    name='TokenRefreshRequest',
    fields={
        'refresh': serializers.CharField(help_text='Refresh token yang masih valid.'),
    },
)

token_pair_response = inline_serializer(
    name='TokenPairResponse',
    fields={
        'refresh': serializers.CharField(help_text='Refresh token untuk memperoleh access token baru.'),
        'access': serializers.CharField(help_text='Access token yang digunakan pada header Authorization.'),
    },
)

token_refresh_response = inline_serializer(
    name='TokenRefreshResponse',
    fields={
        'access': serializers.CharField(help_text='Access token baru hasil pembaruan refresh token.'),
    },
)

verify_email_response = inline_serializer(
    name='VerifyEmailResponse',
    fields={
        'message': serializers.CharField(help_text='Pesan hasil verifikasi email.'),
    },
)


@extend_schema(
    tags=['Autentikasi'],
    summary='Mendaftarkan akun pengguna baru',
    description=(
        'Endpoint ini digunakan untuk membuat akun baru dengan email, nama, '
        'dan kata sandi yang tervalidasi.'
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=register_success_response,
            description='Registrasi berhasil dan akun pengguna telah dibuat.',
        ),
        400: OpenApiResponse(description='Data registrasi tidak valid.'),
    },
    examples=[
        OpenApiExample(
            'Contoh Request Registrasi',
            value={
                'email': 'hannanime12@caerabouquet.shop',
                'name': 'Hanna Fernanda',
                'password': 'Annah123#',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Contoh Respons Registrasi Berhasil',
            value={'message': 'User registered successfully'},
            response_only=True,
            status_codes=['201'],
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    """Menangani proses registrasi pengguna baru.

    View ini menerima data pendaftaran, menjalankan validasi serializer,
    lalu menyimpan akun baru ke dalam sistem.
    """
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """Memproses permintaan registrasi dan mengembalikan respons sukses.

        Args:
            request (Request): Objek request yang memuat data registrasi.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons HTTP 201 setelah pengguna berhasil dibuat.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            security_logger.warning(
                "Validasi registrasi pengguna gagal.",
                extra={"ip": request.META.get("REMOTE_ADDR"), "errors": serializer.errors}
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        try:
            serializer.instance.send_verification_email()
        except Exception:
            security_logger.exception(
                "Pengiriman email verifikasi gagal.",
                extra={"user_id": str(serializer.instance.id), "email": serializer.instance.email}
            )
            return Response(
                {"detail": "Akun berhasil dibuat, tetapi email verifikasi gagal dikirim."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        logger.info(
            "Pengguna berhasil didaftarkan.",
            extra={"user_id": str(serializer.instance.id), "email": serializer.instance.email}
        )

        return Response(
            {"message": "Registrasi berhasil. Silakan cek email untuk verifikasi akun."},
            status=status.HTTP_201_CREATED
        )

@extend_schema(
    tags=['Pengguna'],
    summary='Mengambil profil pengguna saat ini',
    description='Endpoint ini mengembalikan data profil milik pengguna yang sedang terautentikasi.',
    responses={
        200: UserProfileSerializer,
        401: OpenApiResponse(description='Autentikasi diperlukan untuk mengakses profil pengguna.'),
    },
)
class UserProfileView(generics.RetrieveAPIView):
    """Mengambil profil milik pengguna yang sedang terautentikasi.

    View ini digunakan untuk menampilkan data identitas dasar pengguna
    tanpa perlu mengirimkan parameter tambahan.
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """Mengembalikan objek pengguna dari sesi yang sedang aktif.

        Returns:
            User: Pengguna yang sedang login pada request saat ini.
        """
        logger.info(
            "Profil pengguna berhasil diakses.",
            extra={"user_id": str(self.request.user.id)}
        )
        return self.request.user


@extend_schema(
    tags=['Autentikasi'],
    summary='Masuk ke sistem dan mendapatkan token JWT',
    description=(
        'Endpoint login untuk memperoleh `access token` dan `refresh token` '
        'menggunakan email dan kata sandi pengguna.'
    ),
    request=token_pair_request,
    responses={
        200: OpenApiResponse(
            response=token_pair_response,
            description='Login berhasil dan token JWT dikembalikan.',
        ),
        401: OpenApiResponse(description='Email atau kata sandi tidak valid.'),
    },
    examples=[
        OpenApiExample(
            'Contoh Request Login',
            value={
                'email': 'hannanime12@caerabouquet.shop',
                'password': 'Annah123#',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Contoh Respons Login Berhasil',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh-token',
                'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access-token',
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class LoginView(TokenObtainPairView):
    """Menambahkan dokumentasi Swagger dan logging untuk endpoint login JWT.

    View ini tetap menggunakan mekanisme bawaan Simple JWT, lalu
    menambahkan pencatatan log untuk aktivitas login pengguna.
    """
    serializer_class = VerifiedEmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """Memproses login pengguna dan mencatat hasil autentikasi.

        Args:
            request (Request): Objek request yang memuat email dan kata sandi.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons token JWT atau pesan kegagalan autentikasi.
        """
        response = super().post(request, *args, **kwargs)
        email = request.data.get('email', '')
        if response.status_code == status.HTTP_200_OK:
            logger.info(
                "Login pengguna berhasil.",
                extra={"email": email, "ip": request.META.get("REMOTE_ADDR")}
            )
        else:
            security_logger.warning(
                "Login pengguna gagal.",
                extra={"email": email, "ip": request.META.get("REMOTE_ADDR"), "status_code": response.status_code}
            )
        return response


@extend_schema(
    tags=['Autentikasi'],
    summary='Memverifikasi email pengguna',
    description='Endpoint ini memverifikasi email pengguna berdasarkan token yang dikirim melalui email registrasi.',
    parameters=[
        OpenApiParameter(
            name='token',
            description='Token verifikasi email yang dikirim melalui email pengguna.',
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=verify_email_response,
            description='Email pengguna berhasil diverifikasi.',
        ),
        400: OpenApiResponse(description='Token verifikasi tidak valid atau sudah digunakan.'),
    },
    examples=[
        OpenApiExample(
            'Contoh URL Verifikasi Email',
            value='/api/auth/verify-email/?token=9a3a1d9f6e4d4c67b5933c70ef4d24d1',
            parameter_only=('token', 'query'),
        ),
        OpenApiExample(
            'Contoh Respons Verifikasi Berhasil',
            value={
                'message': 'Email berhasil diverifikasi.',
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class VerifyEmailView(generics.GenericAPIView):
    """Memverifikasi email pengguna menggunakan token verifikasi.

    View ini menerima token verifikasi yang dikirim melalui email, lalu
    menandai akun pengguna sebagai terverifikasi jika token valid.
    """

    permission_classes = (AllowAny,)
    serializer_class = serializers.Serializer

    def _verify_email(self, request):
        """Memproses verifikasi email berdasarkan token pengguna.

        Args:
            request (Request): Objek request yang memuat token verifikasi.

        Returns:
            Response: Respons hasil verifikasi email pengguna.
        """
        token = request.query_params.get('token', '').strip()
        if not token:
            security_logger.warning(
                "Verifikasi email gagal karena token tidak diberikan.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
            return Response(
                {"detail": "Token verifikasi wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email_verification_token=token,
            is_email_verified=False,
        ).first()

        if not user:
            security_logger.warning(
                "Verifikasi email gagal karena token tidak valid.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
            return Response(
                {"detail": "Token verifikasi tidak valid atau sudah digunakan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_email_verified = True
        user.email_verification_token = None
        user.save(update_fields=['is_email_verified', 'email_verification_token'])

        logger.info(
            "Email pengguna berhasil diverifikasi.",
            extra={"user_id": str(user.id), "email": user.email}
        )
        return Response(
            {"message": "Email berhasil diverifikasi."},
            status=status.HTTP_200_OK
        )

    def get(self, request, *args, **kwargs):
        """Memproses verifikasi email dari tautan yang dibuka pengguna.

        Args:
            request (Request): Objek request yang memuat token verifikasi.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons hasil verifikasi email pengguna.
        """
        return self._verify_email(request)


@extend_schema(
    tags=['Autentikasi'],
    summary='Memperbarui access token',
    description='Endpoint ini digunakan untuk menghasilkan access token baru dari refresh token yang masih valid.',
    request=token_refresh_request,
    responses={
        200: OpenApiResponse(
            response=token_refresh_response,
            description='Access token baru berhasil dibuat.',
        ),
        401: OpenApiResponse(description='Refresh token tidak valid atau sudah kedaluwarsa.'),
    },
    examples=[
        OpenApiExample(
            'Contoh Request Refresh Token',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh-token',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Contoh Respons Refresh Token Berhasil',
            value={
                'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access-token-baru',
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class TokenRefreshDocsView(TokenRefreshView):
    """Menambahkan dokumentasi Swagger dan logging untuk endpoint refresh token.

    View ini mempertahankan alur refresh token bawaan dan hanya
    menambahkan dokumentasi serta pencatatan log aktivitas.
    """

    def post(self, request, *args, **kwargs):
        """Memproses pembaruan access token dan mencatat hasilnya.

        Args:
            request (Request): Objek request yang memuat refresh token.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons access token baru atau pesan kegagalan refresh.
        """
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(
                "Pembaruan access token berhasil.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
        else:
            security_logger.warning(
                "Pembaruan access token gagal.",
                extra={"ip": request.META.get("REMOTE_ADDR"), "status_code": response.status_code}
            )
        return response