from django.http import JsonResponse
from django.views import View
import sys

class HealthCheckView(View):
    """Health check endpoint для Docker и мониторинга"""

    def get(self, request):
        try:
            # Проверяем подключение к БД
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            return JsonResponse({
                "status": "healthy",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "database": "connected"
            })
        except Exception as e:
            return JsonResponse({
                "status": "unhealthy",
                "error": str(e)
            }, status=503)
