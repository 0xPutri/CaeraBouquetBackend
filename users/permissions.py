from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Membatasi perubahan data hanya untuk pengguna admin.

    Permission ini tetap mengizinkan akses baca untuk semua pengguna,
    tetapi operasi tulis hanya dapat dilakukan oleh staf admin.
    """

    def has_permission(self, request, view):
        """Menentukan apakah request memiliki izin untuk diproses.

        Args:
            request (Request): Objek request yang sedang dievaluasi.
            view (APIView): View yang sedang menerima request.

        Returns:
            bool: Nilai True jika akses diizinkan.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)