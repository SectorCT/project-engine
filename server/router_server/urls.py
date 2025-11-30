from django.urls import path, re_path
import re

from .views import backend_proxy

app_name = 'router'

# UUID pattern: 8-4-4-4-12 hexadecimal digits
uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

urlpatterns = [
    # Explicit project ID routes (highest priority)
    re_path(rf'^(?P<project_id>{uuid_pattern})/$', backend_proxy, name='backend-root'),
    re_path(rf'^(?P<project_id>{uuid_pattern})/(?P<subpath>.*)$', backend_proxy, name='backend-proxy'),
    # Catch-all for asset requests (extracts project_id from Referer header)
    # Exclude API routes, admin, and well-known paths
    # This must be last to not interfere with API routes in main urls.py
    re_path(r'^(?!(api|admin|ws|\.well-known)/)(?P<subpath>.*)$', backend_proxy, name='backend-proxy-catchall'),
]

