"""URL configuration for the projectEngine backend."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_info(_request):
    """Return API information and available endpoints."""
    return JsonResponse(
        {
            'message': 'projectEngine API',
            'version': '1.0',
            'endpoints': {
                'admin': '/admin/',
                'auth': '/api/auth/',
                'jobs': '/api/jobs/',
                'apps': '/api/apps/',
                'websocket': '/ws/jobs/<job_id>/',
            },
        }
    )


urlpatterns = [
    path('', api_info, name='api_info'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/', include('jobs.urls')),
    path('', include('router_server.urls')),
]
