import shlex
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import docker
from docker.errors import APIError, NotFound
from django.conf import settings
from agentLoop.systems.docker_env import get_port_for_project


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
    """Return a cached Docker client using default Docker socket."""
    return docker.from_env()


def get_container_name(project_id: Optional[str]) -> str:
    """Return the container name for a given project/job ID."""
    if project_id:
        return f'project_engine_{project_id}_container'
    return 'project_engine_builder_container'


def resolve_container(project_id: Optional[str]) -> docker.models.containers.Container:
    """
    Return the Docker container for the project/job.

    When a specific project_id is supplied we require that container to exist so
    users cannot accidentally read another job's workspace. Passing None
    explicitly requests the shared builder container.
    """
    client = get_docker_client()
    container_name = get_container_name(project_id) if project_id else get_container_name(None)
    try:
        return client.containers.get(container_name)
    except NotFound as exc:
        raise ContainerNotFound(str(exc)) from exc


def stop_container(project_id: Optional[str]) -> None:
    """
    Stop (but do not delete) the container associated with the given project/job ID.

    This is best-effort: failures are swallowed so API calls don't crash if Docker
    is unreachable.
    """
    client = get_docker_client()
    container_name = get_container_name(project_id)
    try:
        container = client.containers.get(container_name)
    except NotFound:
        return

    try:
        container.stop(timeout=10)
    except APIError:
        pass


def start_container(project_id: str) -> None:
    """
    Ensure the job-specific container is running (restarts if it exists but is stopped).
    """
    client = get_docker_client()
    container_name = get_container_name(project_id)
    try:
        container = client.containers.get(container_name)
    except NotFound as exc:
        raise ContainerNotFound(str(exc)) from exc

    container.reload()
    status = container.attrs.get('State', {}).get('Status')
    if status == 'running':
        return
    try:
        container.start()
    except APIError as exc:
        raise DockerCommandError(f'Failed to start container {container_name}: {exc}') from exc


def get_project_host_port(project_id: str) -> int:
    """
    Return the host port bound to the project's internal port 3000.

    Uses the same deterministic hashing logic as DockerEnv to ensure
    the router points to the correct exposed port.
    """
    return get_port_for_project(project_id)


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

