from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import inline_serializer, extend_schema

health_check_response = inline_serializer(
    name='HealthCheckResponse',
    fields={
        'status': serializers.CharField(),
        'timestamp': serializers.DateTimeField(),
    },
)

class HealthCheckView(APIView):
    """Endpoint sederhana untuk memeriksa kesehatan aplikasi."""

    permission_classes = (AllowAny,)

    @extend_schema(
        tags=['System'],
        summary='Health check aplikasi',
        description='Endpoint ringan untuk memeriksa apakah service backend berjalan.',
        responses={200: health_check_response},
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "ok",
                "timestamp": timezone.now().isoformat(),
            }
        )