import importlib
from typing import Any, Callable, Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _import_orchestrator(path: str) -> Callable[..., Any]:
    module_path, attribute = path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    orchestrator = getattr(module, attribute, None)
    if orchestrator is None:
        raise ImproperlyConfigured(f'Could not find orchestrator callable "{attribute}" in {module_path}')
    return orchestrator


def run_orchestrator(job_id: str, prompt: str, callbacks: Any, **kwargs: Dict[str, Any]) -> Any:
    """Invoke the external multi-agent orchestrator."""
    path = getattr(settings, 'AGENT_ORCHESTRATOR_PATH', '').strip()
    if not path:
        raise ImproperlyConfigured('AGENT_ORCHESTRATOR_PATH must be configured')

    orchestrator = _import_orchestrator(path)
    return orchestrator(job_id=job_id, prompt=prompt, callbacks=callbacks, **kwargs)

