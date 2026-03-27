from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

class HealthCheckView(APIView):
    """Endpoint sederhana untuk memeriksa kesehatan aplikasi."""

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "ok",
                "timestamp": timezone.now().isoformat(),
            }
        )