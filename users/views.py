from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import RegisterSerializer, UserProfileSerializer

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
                'email': 'hannanime12@caera.my.id',
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
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"message": "User registered successfully"},
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
                'email': 'hannanime12@caera.my.id',
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
    """Menambahkan dokumentasi Swagger untuk endpoint login JWT.

    View ini tetap menggunakan perilaku bawaan Simple JWT dan hanya
    memperjelas schema dokumentasi pada Swagger.
    """


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
    """Menambahkan dokumentasi Swagger untuk endpoint refresh token.

    View ini tidak mengubah mekanisme refresh token dan hanya digunakan
    agar dokumentasi endpoint tampil lebih jelas dalam Bahasa Indonesia.
    """