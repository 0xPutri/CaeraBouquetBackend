import logging

from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import inline_serializer, extend_schema

logger = logging.getLogger('caera')

health_check_response = inline_serializer(
    name='HealthCheckResponse',
    fields={
        'status': serializers.CharField(),
        'timestamp': serializers.DateTimeField(),
    },
)


class HealthCheckView(APIView):
    """Menyediakan endpoint sederhana untuk memeriksa kesehatan aplikasi.

    View ini digunakan untuk memastikan service backend masih berjalan
    dan dapat merespons permintaan dasar dari klien.
    """

    permission_classes = (AllowAny,)

    @extend_schema(
        tags=['System'],
        summary='Health check aplikasi',
        description='Endpoint ringan untuk memeriksa apakah service backend berjalan.',
        responses={200: health_check_response},
    )
    def get(self, request, *args, **kwargs):
        """Mengembalikan status kesehatan aplikasi saat ini.

        Args:
            request (Request): Objek request yang memicu health check.
            *args: Argumen tambahan dari kelas induk.
            **kwargs: Argumen keyword tambahan dari kelas induk.

        Returns:
            Response: Respons yang memuat status aplikasi dan waktu server.
        """
        logger.debug("Permintaan health check diterima.")
        return Response(
            {
                "status": "ok",
                "timestamp": timezone.now().isoformat(),
            }
        )