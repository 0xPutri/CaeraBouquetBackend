import logging

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view, inline_serializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import RegisterSerializer, UserProfileSerializer, VerifiedEmailTokenObtainPairSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer

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


@extend_schema_view(
    get=extend_schema(
        tags=['Pengguna'],
        summary='Mengambil profil pengguna saat ini',
        description='Endpoint ini mengembalikan data profil milik pengguna yang sedang terautentikasi.',
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description='Autentikasi diperlukan untuk mengakses profil pengguna.'),
        },
    ),
    put=extend_schema(
        tags=['Pengguna'],
        summary='Memperbarui seluruh profil pengguna',
        description='Endpoint ini memungkinkan pengguna untuk memperbarui seluruh informasi profil mereka.',
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description='Data yang dikirimkan tidak valid.'),
            401: OpenApiResponse(description='Autentikasi diperlukan.'),
        },
    ),
    patch=extend_schema(
        tags=['Pengguna'],
        summary='Memperbarui sebagian profil pengguna',
        description='Endpoint ini memungkinkan pengguna untuk memperbarui sebagian informasi profil mereka, seperti nama atau nomor telepon.',
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description='Data yang dikirimkan tidak valid.'),
            401: OpenApiResponse(description='Autentikasi diperlukan.'),
        },
    )
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """Mengambil dan memperbarui profil milik pengguna yang sedang terautentikasi.

    View ini digunakan untuk menampilkan serta mengubah data identitas dasar
    pengguna tanpa perlu mengirimkan parameter tambahan di URL.
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """Mengembalikan objek pengguna dari sesi yang sedang aktif.

        Returns:
            User: Pengguna yang sedang login pada request saat ini.
        """
        if self.request.method == 'GET':
            logger.info(
                "Profil pengguna berhasil diakses.",
                extra={"user_id": str(self.request.user.id)}
            )
        return self.request.user

    def perform_update(self, serializer):
        """
        Menyimpan pembaruan profil dan mencatat aktivitasnya.

        Fungsi ini dipanggil setelah data yang dikirim berhasil divalidasi,
        lalu menyimpan perubahan tersebut ke dalam database.

        Args:
            serializer (Serializer): Serializer yang telah divalidasi.
        """
        super().perform_update(serializer)
        logger.info(
            "Profil pengguna berhasil diperbarui.",
            extra={"user_id": str(self.request.user.id)}
        )


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


from django.http import HttpResponseRedirect
from django.conf import settings


@extend_schema(
    tags=['Autentikasi'],
    summary='Memverifikasi email pengguna',
    description='Endpoint ini memverifikasi email pengguna berdasarkan token yang dikirim melalui email registrasi, kemudian mengarahkan pengguna ke halaman frontend.',
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
        302: OpenApiResponse(description='Redirect ke halaman frontend (login atau error).'),
    },
)
class VerifyEmailView(generics.GenericAPIView):
    """Memverifikasi email pengguna menggunakan token verifikasi.

    View ini menerima token verifikasi yang dikirim melalui email, lalu
    menandai akun pengguna sebagai terverifikasi jika token valid,
    dan langsung mengarahkan pengguna kembali ke aplikasi frontend.
    """

    permission_classes = (AllowAny,)
    serializer_class = serializers.Serializer

    def get(self, request, *args, **kwargs):
        """Memproses verifikasi email dan mengarahkan ke frontend.

        Args:
            request (Request): Objek request yang memuat token verifikasi.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            HttpResponseRedirect: Mengarahkan pengguna ke antarmuka frontend.
        """
        token = request.query_params.get('token', '').strip()

        raw_url = str(getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'))
        frontend_url = raw_url.lstrip('=').strip(' \'"').rstrip('/')

        if not frontend_url.startswith('http'):
            frontend_url = 'https://' + frontend_url

        if not token:
            security_logger.warning(
                "Verifikasi email gagal karena token tidak diberikan.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
            return HttpResponseRedirect(f"{frontend_url}/login?verify=error&detail=missing_token")

        user = User.objects.filter(
            email_verification_token=token,
            is_email_verified=False,
        ).first()

        if not user:
            security_logger.warning(
                "Verifikasi email gagal karena token tidak valid.",
                extra={"ip": request.META.get("REMOTE_ADDR")}
            )
            return HttpResponseRedirect(f"{frontend_url}/login?verify=error&detail=invalid_token")

        user.is_email_verified = True
        user.email_verification_token = None
        user.save(update_fields=['is_email_verified', 'email_verification_token'])

        logger.info(
            "Email pengguna berhasil diverifikasi.",
            extra={"user_id": str(user.id), "email": user.email}
        )
        return HttpResponseRedirect(f"{frontend_url}/login?verify=success")


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


@extend_schema(
    tags=['Autentikasi'],
    summary='Meminta tautan atur ulang kata sandi',
    description='Endpoint ini memvalidasi email pengguna dan mengirimkan tautan dengan token aman untuk mengatur ulang kata sandi.',
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(description='Instruksi atur ulang kata sandi telah dikirim ke email (jika terdaftar).'),
        400: OpenApiResponse(description='Format email tidak valid.'),
    },
)
class PasswordResetRequestView(generics.GenericAPIView):
    """
    Menangani permintaan pemulihan kata sandi pengguna.

    View ini menerima alamat email, memeriksa keberadaannya di database,
    dan mengirimkan email berisi tautan atur ulang jika akun ditemukan.
    """
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        """
        Memproses permintaan pengiriman email reset sandi.

        Args:
            request (Request): Objek request HTTP yang memuat data email.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Konfirmasi bahwa permintaan telah diproses.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        
        if user:
            user.send_password_reset_email()
            
        return Response(
            {"message": "Jika email terdaftar, instruksi atur ulang kata sandi telah dikirim."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Autentikasi'],
    summary='Mengonfirmasi kata sandi baru',
    description='Endpoint ini memvalidasi token dan menyimpan kata sandi baru pengguna.',
    request=PasswordResetConfirmSerializer,
    responses={
        200: OpenApiResponse(description='Kata sandi berhasil diatur ulang.'),
        400: OpenApiResponse(description='Data tidak valid atau token kedaluwarsa.'),
    },
)
class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Menangani proses perubahan kata sandi dengan token.

    View ini memvalidasi token keamanan dan menyetel kata sandi baru
    untuk pengguna yang memintanya.
    """
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        """
        Memproses penggantian kata sandi menggunakan token.

        Args:
            request (Request): Objek request HTTP yang memuat token dan kata sandi baru.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Konfirmasi bahwa kata sandi telah diperbarui atau pesan galat.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        uidb64 = serializer.validated_data['uid']
        new_password = serializer.validated_data['new_password']
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        token_generator = PasswordResetTokenGenerator()
        if user is not None and token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save(update_fields=['password'])
            logger.info("Kata sandi berhasil diatur ulang.", extra={"user_id": str(user.id)})
            return Response(
                {"message": "Kata sandi berhasil diatur ulang. Silakan login kembali."},
                status=status.HTTP_200_OK
            )
            
        security_logger.warning(
            "Percobaan atur ulang kata sandi gagal karena token tidak valid.",
            extra={"ip": request.META.get("REMOTE_ADDR"), "uid": uidb64}
        )
        return Response(
            {"error": "Tautan atur ulang kata sandi tidak valid atau sudah kedaluwarsa."},
            status=status.HTTP_400_BAD_REQUEST
        )