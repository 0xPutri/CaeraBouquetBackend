import logging

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('caera')
security_logger = logging.getLogger('caera.security')


def global_exception_handler(exc, context):
    """Menangani exception DRF secara global dengan format yang konsisten.

    Fungsi ini meneruskan exception ke handler bawaan DRF, lalu
    menambahkan logging terpusat untuk kebutuhan audit dan debugging.

    Args:
        exc (Exception): Exception yang muncul saat request diproses.
        context (dict): Konteks request dan view yang terkait.

    Returns:
        Response: Respons error dari DRF atau respons fallback server.
    """
    response = drf_exception_handler(exc, context)

    request = context.get('request')
    view = context.get('view')
    request_path = request.path if request else None
    request_method = request.method if request else None
    view_name = view.__class__.__name__ if view else None

    if response is not None:
        if response.status_code >= 500:
            security_logger.error(
                "Exception server pada DRF berhasil ditangani.",
                extra={
                    "path": request_path,
                    "method": request_method,
                    "view": view_name,
                    "status_code": response.status_code,
                }
            )
        return response

    security_logger.exception(
        "Exception pada view DRF tidak tertangani.",
        extra={
            "path": request_path,
            "method": request_method,
            "view": view_name,
        }
    )
    return Response(
        {"detail": "Terjadi kesalahan pada server."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )