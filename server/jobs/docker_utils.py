import shlex
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import docker
from docker.errors import APIError, NotFound
from django.conf import settings


class ContainerNotFound(Exception):
    """Raised when the requested build container does not exist."""


class ContainerNotRunning(Exception):
    """Raised when the build container exists but is not running."""


class DockerCommandError(Exception):
    """Raised when a command executed inside the container fails."""


DOCKER_EXCLUDE_PATTERNS: Tuple[str, ...] = (
    '*/node_modules/*',
    '*/node_modules',
    '/app/node_modules',
    '*/.git/*',
    '*/dist/*',
    '*/dist',
    '*/build/*',
    '*/build',
)


@lru_cache(maxsize=1)
def get_docker_client() -> docker.DockerClient:
    """Return a cached Docker client configured either via settings or env."""
    base_url = getattr(settings, 'DOCKER_SOCKET_PATH', None)
    if base_url:
        return docker.DockerClient(base_url=base_url)
    return docker.from_env()


def get_container_name(project_id: Optional[str]) -> str:
    """Return the container name for a given project/job ID."""
    if project_id:
        return f'project_engine_{project_id}_container'
    return 'project_engine_builder_container'


def resolve_container(project_id: Optional[str]) -> docker.models.containers.Container:
    """
    Return the Docker container for the project/job.

    Falls back to the default builder container if the job-specific container
    does not exist yet (current behaviour of the builder).
    """
    client = get_docker_client()
    search_order: List[str] = []
    if project_id:
        search_order.append(get_container_name(project_id))
    search_order.append(get_container_name(None))

    last_error: Optional[Exception] = None
    for name in search_order:
        try:
            container = client.containers.get(name)
            return container
        except NotFound as exc:
            last_error = exc
            continue
    raise ContainerNotFound(str(last_error))


def ensure_container_running(container: docker.models.containers.Container) -> None:
    """Raise ContainerNotRunning if the container is not in running state."""
    container.reload()
    status = container.attrs.get('State', {}).get('Status')
    if status != 'running':
        raise ContainerNotRunning(status or 'unknown')


def _build_exclude_clause(patterns: Iterable[str]) -> str:
    return ' '.join(f'-not -path {shlex.quote(pattern)}' for pattern in patterns)


def exec_in_container(
    container: docker.models.containers.Container,
    command: Union[str, Sequence[str]],
    workdir: str = '/app',
) -> Tuple[int, str]:
    """Execute a command inside the container and return exit code + output."""
    exit_code, output = container.exec_run(
        command,
        workdir=workdir,
        stdout=True,
        stderr=True,
        demux=False,
    )
    decoded = output.decode('utf-8', errors='replace') if isinstance(output, (bytes, bytearray)) else str(output)
    return exit_code, decoded


def build_find_command(path: str, resource_type: str, limit: int) -> str:
    exclude_clause = _build_exclude_clause(DOCKER_EXCLUDE_PATTERNS)
    safe_path = shlex.quote(path)
    return f'find {safe_path} -type {resource_type} {exclude_clause} | head -{limit}'


def build_stat_command(limit: int) -> str:
    exclude_clause = _build_exclude_clause(DOCKER_EXCLUDE_PATTERNS)
    # %T@ → modification time (epoch float), %s → size, %p → path
    return (
        'find /app -type f '
        f'{exclude_clause} '
        r"-printf '%T@|%s|%p\n' "
        f'| head -{limit}'
    )

