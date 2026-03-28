import logging
from django.http import JsonResponse

security_logger = logging.getLogger('caera.security')


class GlobalAPIExceptionMiddleware:
    """Menangani exception API sebagai lapisan fallback global.

    Middleware ini menangkap error yang lolos dari lapisan lain agar
    endpoint API tetap mengembalikan respons JSON yang konsisten.
    """

    def __init__(self, get_response):
        """Menyimpan callable utama untuk memproses request berikutnya.

        Args:
            get_response (Callable): Callable yang meneruskan request ke lapisan berikutnya.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Memproses request dan menangani exception yang tidak tertangani.

        Args:
            request (HttpRequest): Request yang sedang diproses.

        Returns:
            HttpResponse: Respons normal aplikasi atau respons JSON fallback.
        """
        try:
            return self.get_response(request)
        except Exception:
            if request.path.startswith('/api/'):
                security_logger.exception(
                    "Exception pada lapisan middleware Django tidak tertangani.",
                    extra={"path": request.path, "method": request.method}
                )
                return JsonResponse(
                    {"detail": "Terjadi kesalahan pada server."},
                    status=500
                )
            raise