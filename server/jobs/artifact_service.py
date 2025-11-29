import logging
import posixpath
import shlex
from typing import Dict, List, Optional

from django.utils import timezone

from .docker_utils import (
    ContainerNotFound,
    ContainerNotRunning,
    build_find_command,
    build_stat_command,
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


def _build_tree(entries: List[str]) -> Dict[str, dict]:
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
            is_file = idx == len(parts) - 1
            node = cursor.setdefault(
                part,
                {
                    'name': part,
                    'path': entry if is_file else None,
                    'type': 'file' if is_file else 'dir',
                    'children': {} if not is_file else None,
                },
            )
            if is_file:
                node['path'] = entry
                node['type'] = 'file'
                node['children'] = None
            else:
                if node['children'] is None:
                    node['children'] = {}
                cursor = node['children']
    return tree


def _tree_to_list(tree: Dict[str, dict]) -> List[dict]:
    items: List[dict] = []
    for key in sorted(tree.keys()):
        node = tree[key]
        data = {'name': node['name'], 'path': node['path'], 'type': node['type']}
        if node['type'] == 'dir' and node.get('children'):
            data['children'] = _tree_to_list(node['children'])
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

        tree = _build_tree(dirs)
        file_tree = _build_tree(files)

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



