import logging
from urllib.parse import urljoin

import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from jobs.docker_utils import (
    ContainerNotFound,
    DockerCommandError,
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


@csrf_exempt
def backend_proxy(request, project_id, subpath=''):
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

    host_port = get_project_host_port(str(job.id))
    base_url = f'http://127.0.0.1:{host_port}/'
    forward_url = urljoin(base_url, subpath)
    if request.META.get('QUERY_STRING'):
        forward_url = f'{forward_url}?{request.META["QUERY_STRING"]}'

    headers = _build_forward_headers(request)
    headers['Host'] = f'127.0.0.1:{host_port}'

    try:
        upstream = requests.request(
            method=request.method,
            url=forward_url,
            headers=headers,
            params=None,  # already encoded in QUERY_STRING
            data=request.body,
            cookies=request.COOKIES,
            allow_redirects=False,
            stream=True,
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning('Reverse proxy request failed for %s: %s', job.id, exc)
        return JsonResponse({'detail': 'Project backend unavailable.'}, status=503)

    response = StreamingHttpResponse(
        streaming_content=upstream.iter_content(chunk_size=64 * 1024),
        status=upstream.status_code,
        reason=upstream.reason,
    )

    for key, value in upstream.headers.items():
        lower = key.lower()
        if lower in HOP_BY_HOP_HEADERS:
            continue
        response[key] = value
    return response

