import base64
import logging
import posixpath
import shlex
from datetime import datetime
from typing import Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from .docker_utils import (
    ContainerNotFound,
    ContainerNotRunning,
    build_find_command,
    ensure_container_running,
    exec_in_container,
    resolve_container,
)

logger = logging.getLogger(__name__)


class FileStructureError(Exception):
    """Raised when the file structure cannot be retrieved."""

    def __init__(self, message: str, kind: str = 'error'):
        super().__init__(message)
        self.kind = kind


class FileContentError(Exception):
    """Raised when a file cannot be read."""

    def __init__(self, message: str, kind: str = 'error'):
        super().__init__(message)
        self.kind = kind


class FileWriteError(Exception):
    """Raised when a file cannot be written."""

    def __init__(self, message: str, kind: str = 'error'):
        super().__init__(message)
        self.kind = kind


def _normalize_path(raw_path: str) -> str:
    if not raw_path:
        raise FileContentError('File path is required')
    if raw_path.startswith('/app'):
        normalized = raw_path
    else:
        sanitized = raw_path.lstrip('/')
        normalized = f'/app/{sanitized}'

    normalized = posixpath.normpath(normalized)
    if not normalized.startswith('/app'):
        raise FileContentError('Invalid path')
    return normalized


def _build_tree(entries: List[str], entry_type: str = 'file') -> Dict[str, dict]:
    """
    Build a tree structure from file or directory paths.
    
    Args:
        entries: List of absolute paths (e.g., ['/app/src/App.tsx', '/app/src/components'])
        entry_type: 'file' or 'dir' - determines the type of the leaf nodes
    """
    tree: Dict[str, dict] = {}
    for entry in entries:
        rel_path = entry.replace('/app', '').lstrip('/')
        if not rel_path:
            continue
        parts = [p for p in rel_path.split('/') if p not in ('.', '..', '')]
        if not parts:
            continue

        cursor = tree
        for idx, part in enumerate(parts):
            is_leaf = idx == len(parts) - 1
            node = cursor.setdefault(
                part,
                {
                    'name': part,
                    'path': entry if is_leaf else None,
                    'type': entry_type if is_leaf else 'dir',
                    'children': {} if not is_leaf else None,
                },
            )
            if is_leaf:
                # Leaf node - set the type and path
                node['path'] = entry
                node['type'] = entry_type
                if entry_type == 'file':
                    node['children'] = None
                else:
                    # For directories, ensure children dict exists
                    if node['children'] is None:
                        node['children'] = {}
            else:
                # Intermediate node - always a directory
                node['type'] = 'dir'
                if node['children'] is None:
                    node['children'] = {}
                cursor = node['children']
    return tree


def _tree_to_list(tree: Dict[str, dict]) -> List[dict]:
    items: List[dict] = []
    for key in sorted(tree.keys()):
        node = tree[key]
        data = {'name': node['name'], 'path': node['path'], 'type': node['type']}
        if node['type'] == 'dir':
            # Always include children for directories, even if empty
            # This ensures empty directories are properly represented
            if node.get('children') is not None:
                children_list = _tree_to_list(node['children'])
                data['children'] = children_list
            else:
                # Directory with no children property - should not happen, but handle it
                data['children'] = []
        items.append(data)
    return items


def get_file_structure(job_id: str, path: str = '/app', limit: int = 200) -> List[dict]:
    normalized = _normalize_path(path or '/app')

    try:
        container = resolve_container(job_id)
        ensure_container_running(container)
        file_cmd = build_find_command(normalized, 'f', limit)
        dir_cmd = build_find_command(normalized, 'd', limit)
        file_exit, file_output = exec_in_container(container, ['sh', '-c', file_cmd], workdir='/app')
        dir_exit, dir_output = exec_in_container(container, ['sh', '-c', dir_cmd], workdir='/app')
        if file_exit != 0 or dir_exit != 0:
            raise FileStructureError('Failed to enumerate files inside container')
        files = [line.strip() for line in file_output.splitlines() if line.strip()]
        dirs = [line.strip() for line in dir_output.splitlines() if line.strip()]

        # Build trees with correct types
        tree = _build_tree(dirs, entry_type='dir')
        file_tree = _build_tree(files, entry_type='file')

        # Merge file tree entries into directory tree
        for key, value in file_tree.items():
            if key not in tree:
                tree[key] = value
            else:
                # merge children if directories share same name
                if value.get('children'):
                    tree[key].setdefault('children', {}).update(value['children'])
        return _tree_to_list(tree)
    except ContainerNotFound as exc:
        raise FileStructureError('Container not found', kind='not_found') from exc
    except ContainerNotRunning as exc:
        raise FileStructureError('Container is not running', kind='not_running') from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('Failed to get file structure for job %s', job_id)
        raise FileStructureError(str(exc)) from exc


def read_file(job_id: str, path: str) -> Dict[str, str]:
    normalized = _normalize_path(path)
    try:
        container = resolve_container(job_id)
        ensure_container_running(container)
        exit_code, output = exec_in_container(
            container,
            ['sh', '-c', f'cat {shlex.quote(normalized)}'],
            workdir='/app',
        )
        if exit_code != 0:
            raise FileContentError('File not found or cannot be read', kind='not_found')
        return {'path': normalized, 'content': output, 'size': len(output)}
    except ContainerNotFound as exc:
        raise FileContentError('Container not found', kind='not_found') from exc
    except ContainerNotRunning as exc:
        raise FileContentError('Container is not running', kind='not_running') from exc
    except FileContentError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('Failed to read file %s for job %s', normalized, job_id)
        raise FileContentError(str(exc)) from exc


def write_file(job_id: str, path: str, content: str, *, encoding: str = 'utf-8') -> Dict[str, str]:
    normalized = _normalize_path(path)
    if not isinstance(content, str):
        raise FileWriteError('Content must be a string')
    max_bytes = getattr(settings, 'ARTIFACT_MAX_WRITE_BYTES', 512 * 1024)
    payload = content.encode(encoding)
    if len(payload) > max_bytes:
        raise FileWriteError(f'File content exceeds limit of {max_bytes} bytes')

    b64_content = base64.b64encode(payload).decode('ascii')
    script = (
        "import base64, pathlib\n"
        f"path = pathlib.Path({repr(normalized)})\n"
        f"data = base64.b64decode({repr(b64_content)})\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_bytes(data)\n"
    )

    try:
        container = resolve_container(job_id)
        ensure_container_running(container)

        def _run_python(cmd: str) -> bool:
            exit_code, _ = exec_in_container(container, cmd, workdir='/app')
            return exit_code == 0

        if not (
            _run_python(['python3', '-c', script])
            or _run_python(['python', '-c', script])
        ):
            raise FileWriteError('Failed to write file')

        stat_exit, stat_output = exec_in_container(
            container,
            ['stat', '-c', '%Y|%s', normalized],
            workdir='/app',
        )
        modified_ts = timezone.now().isoformat()
        size_on_disk = len(payload)
        if stat_exit == 0:
            parts = stat_output.strip().split('|')
            if len(parts) == 2:
                try:
                    modified_ts = datetime.fromtimestamp(float(parts[0]), tz=timezone.utc).isoformat()
                    size_on_disk = int(parts[1])
                except Exception:  # pragma: no cover - best effort parsing
                    pass

        return {
            'path': normalized,
            'bytes_written': len(payload),
            'size': size_on_disk,
            'modified_at': modified_ts,
        }
    except ContainerNotFound as exc:
        raise FileWriteError('Container not found', kind='not_found') from exc
    except ContainerNotRunning as exc:
        raise FileWriteError('Container is not running', kind='not_running') from exc
    except FileWriteError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('Failed to write file %s for job %s', normalized, job_id)
        raise FileWriteError(str(exc)) from exc
