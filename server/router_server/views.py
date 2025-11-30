import logging
import time
from urllib.parse import urljoin

import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from jobs.docker_utils import (
    ContainerNotFound,
    DockerCommandError,
    get_container_name,
    get_docker_client,
    get_project_host_port,
    start_container,
)
from jobs.models import Job


logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}


def _build_forward_headers(request):
    headers = {}
    for key, value in request.headers.items():
        lower = key.lower()
        if lower in HOP_BY_HOP_HEADERS:
            continue
        if lower == 'host':
            continue
        headers[key] = value
    return headers


def _extract_project_id_from_referer(request):
    """Extract project ID from Referer or Origin header if present."""
    import re
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    
    # Try Referer first
    referer = request.META.get('HTTP_REFERER', '')
    if referer:
        match = re.search(uuid_pattern, referer)
        if match:
            return match.group(0)
    
    # Fallback to Origin header
    origin = request.META.get('HTTP_ORIGIN', '')
    if origin:
        match = re.search(uuid_pattern, origin)
        if match:
            return match.group(0)
    
    return None


@csrf_exempt
def backend_proxy(request, project_id=None, subpath=''):
    # Normalize subpath first: remove leading slash if present, and handle trailing slashes for file requests
    if subpath:
        subpath = subpath.lstrip('/')
        # For file-like paths (with extensions), remove trailing slash
        # This handles cases like /src/main.tsx/ -> /src/main.tsx
        # Check if the last non-empty segment contains a dot (file extension)
        if subpath.endswith('/'):
            parts = [p for p in subpath.rstrip('/').split('/') if p]
            if parts and '.' in parts[-1]:
                subpath = subpath.rstrip('/')
                logger.debug('Removed trailing slash from file path: %s', subpath)
    
    # IMPORTANT: If subpath starts with the project ID, strip it
    # This happens when React Router navigates to routes like /{project_id}/login
    # We want to forward just /login to the container
    if project_id and subpath:
        project_prefix = f'{project_id}/'
        if subpath.startswith(project_prefix):
            subpath = subpath[len(project_prefix):]
            logger.debug('Stripped project ID prefix from subpath: %s', subpath)
        elif subpath == project_id:
            # If subpath is just the project ID, treat it as root
            subpath = ''
    
    # If project_id is not provided, try multiple methods to find it
    if project_id is None:
        # 1. Try to extract from Referer/Origin headers
        project_id = _extract_project_id_from_referer(request)
        
        # 2. Try to extract from cookie (set when main page is loaded)
        if project_id is None:
            project_id = request.COOKIES.get('project_id')
            if project_id:
                try:
                    # Validate it's a valid UUID
                    import uuid
                    uuid.UUID(project_id)
                except (ValueError, TypeError):
                    project_id = None
        
        # 3. Try to extract from session
        if project_id is None and hasattr(request, 'session'):
            project_id = request.session.get('project_id')
        
        if project_id is None:
            # Log for debugging - this helps identify why some requests aren't being proxied
            referer = request.META.get('HTTP_REFERER', '')
            origin = request.META.get('HTTP_ORIGIN', '')
            logger.warning('No project ID found for path %s. Referer: %s, Origin: %s', 
                          request.path, referer, origin)
            return JsonResponse({'detail': 'Project ID not found in URL, Referer header, cookie, or session.'}, status=404)
    
    job = Job.objects.filter(id=project_id).first()
    if job is None:
        return JsonResponse({'detail': 'Unknown project backend.'}, status=404)

    try:
        start_container(str(job.id))
    except ContainerNotFound:
        return JsonResponse({'detail': 'Project container not found.'}, status=404)
    except DockerCommandError as exc:  # pragma: no cover - defensive
        logger.exception('Unable to start container for job %s: %s', job.id, exc)
        return JsonResponse({'detail': 'Failed to start project container.'}, status=503)
    except Exception as exc:  # pragma: no cover
        logger.exception('Unexpected error starting container %s: %s', job.id, exc)
        return JsonResponse({'detail': 'Unexpected container error.'}, status=503)

    # Get container IP address to connect directly (avoids host port mapping issues)
    # Since web container and project containers are on different networks,
    # we connect directly to the container's IP on the internal port 3000
    client = get_docker_client()
    container_name = get_container_name(str(job.id))
    container_ip = None
    host_port = get_project_host_port(str(job.id))  # Keep for logging
    
    try:
        container = client.containers.get(container_name)
        # Get container IP from bridge network (default network)
        networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
        # Try bridge network first (most common)
        if 'bridge' in networks:
            container_ip = networks['bridge'].get('IPAddress')
        elif networks:
            # Fallback to first available network
            first_net = list(networks.values())[0]
            container_ip = first_net.get('IPAddress')
        
        if container_ip:
            logger.info('Proxy for project %s: connecting to container IP %s:3000 (host port %d, subpath: %s)', 
                       job.id, container_ip, host_port, subpath)
        else:
            logger.warning('Could not get container IP for project %s, falling back to host.docker.internal', job.id)
            container_ip = None
    except Exception as e:
        logger.warning('Could not get container IP for project %s: %s. Falling back to host.docker.internal', 
                      job.id, str(e))
        container_ip = None
    
    # Try multiple connection methods in order of preference:
    # 1. host.docker.internal (works on Docker Desktop and Linux with proper setup)
    # 2. Container IP on bridge network (may not work if web container is on different network)
    # 3. 127.0.0.1 (unlikely to work from inside container)
    
    # Prefer host.docker.internal since it's most reliable across different Docker setups
    base_url = None
    connection_method = None
    
    # Try multiple connection methods in order of preference:
    # 1. host.docker.internal (works on Docker Desktop and Linux with extra_hosts)
    # 2. Docker gateway IP (172.17.0.1) - works on Linux to reach host ports
    # 3. Container IP on bridge network (may not work if web container is on different network)
    # 4. 127.0.0.1 (unlikely to work from inside container)
    
    base_url = None
    connection_method = None
    
    # Try host.docker.internal first
    try:
        import socket
        socket.gethostbyname('host.docker.internal')
        base_url = f'http://host.docker.internal:{host_port}/'
        connection_method = f'host.docker.internal:{host_port}'
        logger.info('Using host.docker.internal:%d for project %s', host_port, job.id)
    except (socket.gaierror, Exception):
        # Fallback to Docker gateway IP (172.17.0.1) - this is the host's IP from container perspective
        try:
            # Try to get gateway IP from container's network settings
            if container:
                networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                gateway_ip = None
                if 'bridge' in networks:
                    gateway_ip = networks['bridge'].get('Gateway')
                
                if gateway_ip:
                    base_url = f'http://{gateway_ip}:{host_port}/'
                    connection_method = f'{gateway_ip}:{host_port}'
                    logger.info('Using Docker gateway %s:%d for project %s (host.docker.internal not available)', 
                               gateway_ip, host_port, job.id)
                else:
                    # Default to 172.17.0.1 (standard Docker bridge gateway)
                    base_url = f'http://172.17.0.1:{host_port}/'
                    connection_method = f'172.17.0.1:{host_port}'
                    logger.info('Using default Docker gateway 172.17.0.1:%d for project %s', host_port, job.id)
            else:
                # Default to 172.17.0.1 if we can't get container info
                base_url = f'http://172.17.0.1:{host_port}/'
                connection_method = f'172.17.0.1:{host_port}'
                logger.info('Using default Docker gateway 172.17.0.1:%d for project %s (container info unavailable)', 
                           host_port, job.id)
        except Exception as e:
            logger.warning('Could not determine gateway IP: %s. Trying container IP...', str(e))
            # Fallback to container IP if gateway approach fails
            if container_ip:
                base_url = f'http://{container_ip}:3000/'
                connection_method = f'{container_ip}:3000'
                logger.info('Using container IP %s:3000 for project %s (gateway unavailable)', 
                           container_ip, job.id)
            else:
                # Last resort: 127.0.0.1 (unlikely to work)
                base_url = f'http://127.0.0.1:{host_port}/'
                connection_method = f'127.0.0.1:{host_port}'
                logger.warning('Using 127.0.0.1:%d for project %s (all other methods unavailable)', 
                              host_port, job.id)
    
    forward_url = urljoin(base_url, subpath)
    if request.META.get('QUERY_STRING'):
        forward_url = f'{forward_url}?{request.META["QUERY_STRING"]}'
    
    logger.debug('Proxy forwarding to: %s (method: %s)', forward_url, request.method)

    headers = _build_forward_headers(request)
    # Set Host header based on connection method
    if 'host.docker.internal' in base_url:
        headers['Host'] = f'localhost:{host_port}'
    elif container_ip and f'{container_ip}:3000' in base_url:
        headers['Host'] = f'{container_ip}:3000'
    else:
        headers['Host'] = f'127.0.0.1:{host_port}'

    # Retry logic: wait for service to be ready (container might be starting)
    # The service inside the container (Vite/Express) may need a moment to start
    max_retries = 3
    retry_delay = 0.5  # Start with 0.5 seconds
    upstream = None
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.debug('Proxy attempt %d/%d for %s: %s -> %s', 
                        attempt + 1, max_retries, job.id, request.method, forward_url)
            upstream = requests.request(
                method=request.method,
                url=forward_url,
                headers=headers,
                params=None,  # already encoded in QUERY_STRING
                data=request.body,
                cookies=request.COOKIES,
                allow_redirects=False,
                stream=True,
                timeout=(10, 30),  # (connect timeout, read timeout)
            )
            logger.info('Proxy request successful for %s: %s %s -> %d', 
                       job.id, request.method, subpath, upstream.status_code)
            # Success - break out of retry loop
            break
        except requests.Timeout as exc:
            last_exception = exc
            logger.warning('Proxy request timeout for %s (attempt %d/%d) to %s: %s', 
                          job.id, attempt + 1, max_retries, connection_method, exc)
            if attempt < max_retries - 1:
                logger.debug('Retrying in %.1fs...', retry_delay)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                return JsonResponse({
                    'detail': f'Project backend timeout. Connection to {connection_method} timed out.'
                }, status=504)
        except requests.ConnectionError as exc:
            last_exception = exc
            # Connection refused - service might still be starting
            logger.warning('Proxy connection error for %s (attempt %d/%d) to %s: %s', 
                          job.id, attempt + 1, max_retries, connection_method, exc)
            if attempt < max_retries - 1:
                logger.debug('Service not ready for %s, retrying in %.1fs...', job.id, retry_delay)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Last attempt failed
                logger.error('Reverse proxy request failed for %s after %d attempts to %s: %s', 
                            job.id, max_retries, connection_method, exc)
                return JsonResponse({
                    'detail': f'Project backend unavailable. Cannot connect to {connection_method}. Service may still be starting.'
                }, status=503)
        except requests.RequestException as exc:
            # Other request errors - don't retry
            logger.error('Reverse proxy request failed for %s: %s', job.id, exc)
            return JsonResponse({'detail': f'Project backend error: {str(exc)}'}, status=503)
    
    # If we exhausted all retries without success
    if upstream is None:
        if last_exception:
            logger.warning('Reverse proxy request failed for %s after %d attempts: %s', 
                        job.id, max_retries, last_exception)
        return JsonResponse({'detail': 'Project backend unavailable. Service may still be starting.'}, status=503)

    # Check if this is an HTML response that needs path rewriting
    content_type = upstream.headers.get('Content-Type', '').lower()
    is_html = 'text/html' in content_type
    
    if is_html:
        # For HTML responses, we need to rewrite the content to:
        # 1. Inject a <base> tag so relative assets work
        # 2. Inject a script to strip project ID from pathname for React Router
        # Read the full response content (HTML is typically small enough)
        content = b''.join(upstream.iter_content(chunk_size=64 * 1024))
        html_content = content.decode('utf-8', errors='ignore')
        
        # Inject base tag and minimal pathname rewrite script
        # The proxy strips project ID from subpath, but React Router reads window.location.pathname
        # We need a blocking script to rewrite the pathname before React Router initializes
        import re
        base_path = f'/{project_id}/'
        
        # CRITICAL: Inject blocking script IMMEDIATELY after <head> - must be first
        # This script rewrites pathname synchronously before ANY other script runs
        # React Router reads window.location.pathname, so we must change it first
        # Note: Using double braces {{}} to escape braces in f-string
        pathname_script = f'''<script>
!function(){{var p='/{project_id}';var l=location;if(l.pathname.indexOf(p)===0){{var np=l.pathname.slice(p.length)||'/';history.replaceState({{{{}}}},'',np+l.search+l.hash);}}}
</script>'''
        
        # Inject script as the VERY FIRST thing after <head> (before base tag even)
        head_pattern = r'(<head[^>]*>)'
        # Always inject script first, then base tag
        if '<base' not in html_content.lower():
            injection = f'\\1\n{pathname_script}\n    <base href="{base_path}">'
        else:
            # If base exists, inject script before it
            html_content = re.sub(r'(<head[^>]*>)(.*?)(<base)', f'\\1{pathname_script}\\2\\3', html_content, flags=re.IGNORECASE | re.DOTALL, count=1)
            # Don't do the second substitution if we already did the above
            if pathname_script not in html_content:
                html_content = re.sub(head_pattern, f'\\1\n{pathname_script}', html_content, flags=re.IGNORECASE, count=1)
            else:
                injection = None
        
        if injection:
            html_content = re.sub(head_pattern, injection, html_content, flags=re.IGNORECASE, count=1)
        
        # Create response with rewritten HTML
        response = StreamingHttpResponse(
            [html_content.encode('utf-8')],
            status=upstream.status_code,
            reason=upstream.reason,
        )
    else:
        # For non-HTML responses, stream as-is
        response = StreamingHttpResponse(
            streaming_content=upstream.iter_content(chunk_size=64 * 1024),
            status=upstream.status_code,
            reason=upstream.reason,
        )

    # Set a cookie with the project ID so subsequent requests (like Vite client requests)
    # can find the project ID even if Referer/Origin don't contain it
    response.set_cookie(
        'project_id',
        str(job.id),
        max_age=3600,  # 1 hour
        path='/',
        samesite='Lax',
    )

    # Preserve all headers from upstream, including Content-Type for proper JSON/HTML handling
    # This ensures success messages, JSON responses, and redirects are all handled correctly
    for key, value in upstream.headers.items():
        lower = key.lower()
        if lower in HOP_BY_HOP_HEADERS:
            continue
        # Use the original header name to preserve case (important for some headers)
        response[key] = value
    
    return response

