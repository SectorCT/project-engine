"""
Adapters that expose the agentLoop pipeline to the Django backend.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings

AGENT_LOOP_PATH = Path(getattr(settings, 'AGENT_LOOP_PATH', Path(settings.BASE_DIR) / 'agentLoop'))

if AGENT_LOOP_PATH.exists() and str(AGENT_LOOP_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_LOOP_PATH))

try:  # pragma: no cover - exercised at runtime
    from requirements.gatherer import RequirementsGatherer
    from discussion.orchestrator import Orchestrator
    from output.prd_generator import PRDGenerator
    from agents.pm_agent import PMAgent
    from build import run_ticket_builder as agent_run_ticket_builder
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "agentLoop package could not be imported. "
        "Ensure AGENT_LOOP_PATH is set correctly and dependencies are installed."
    ) from exc


def start_requirements_session(initial_idea: str, state: Optional[Dict] = None) -> Dict:
    gatherer = RequirementsGatherer(state=state)
    return gatherer.start(initial_idea)


def handle_requirements_message(message: str, state: Dict) -> Dict:
    gatherer = RequirementsGatherer(state=state)
    if not gatherer.started:
        raise RuntimeError('Requirements session has not been started')
    return gatherer.handle_user_message(message)


def force_requirements_summary(state: Dict) -> Dict:
    gatherer = RequirementsGatherer(state=state)
    return gatherer.force_summary()


def run_executive_flow(requirements_summary: str) -> List[Dict[str, str]]:
    orchestrator = Orchestrator(requirements_summary)
    return orchestrator.start_discussion()


def get_prd_renderer():
    return PRDGenerator()


def generate_tickets_from_prd(prd_markdown: str, project_structure: Optional[Dict] = None) -> List[Dict]:
    """
    Use the PM agent to break a PRD into epics/stories.
    """
    pm_agent = PMAgent()
    return pm_agent.generate_tickets(prd_markdown, project_structure=project_structure)


def run_ticket_builder(job_id: str, callbacks: Optional[object] = None):
    return agent_run_ticket_builder(job_id=job_id, callbacks=callbacks)

