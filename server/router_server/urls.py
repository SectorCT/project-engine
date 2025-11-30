from django.urls import path

from .views import backend_proxy

app_name = 'router'

urlpatterns = [
    path('<slug:project_id>/', backend_proxy, name='backend-root'),
    path('<slug:project_id>/<path:subpath>/', backend_proxy, name='backend-proxy'),
]

