from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from .serializers import RegisterSerializer, UserProfileSerializer

@extend_schema(tags=['Autentikasi'])
class RegisterView(generics.CreateAPIView):
    """Mendaftarkan pengguna baru ke dalam sistem."""
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )

@extend_schema(tags=['Pengguna'])
class UserProfileView(generics.RetrieveAPIView):
    """Mendapatkan data profil pengguna yang sedang login."""
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user