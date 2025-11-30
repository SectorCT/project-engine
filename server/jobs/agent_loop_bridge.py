"""
Adapters that expose the agentLoop pipeline to the Django backend.
"""
from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings

AGENT_LOOP_PATH = Path(getattr(settings, 'AGENT_LOOP_PATH', Path(settings.BASE_DIR) / 'agentLoop'))

if AGENT_LOOP_PATH.exists() and str(AGENT_LOOP_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_LOOP_PATH))

try:  # pragma: no cover - exercised at runtime
    from requirements.gatherer import RequirementsGatherer
    from discussion.orchestrator import Orchestrator
    from output.prd_generator import PRDGenerator
    from agents.ba_agent import BAAgent
    from agents.master_pm_agent import MasterPMAgent
    from agents.frontend_pm_agent import FrontendPMAgent
    from agents.backend_pm_agent import BackendPMAgent
    from systems.project_initializer import ProjectInitializer
    from agents.pm_agent import PMAgent  # legacy fallback
    from build import run_ticket_builder as agent_run_ticket_builder
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "agentLoop package could not be imported. "
        "Ensure AGENT_LOOP_PATH is set correctly and dependencies are installed."
    ) from exc

logger = logging.getLogger(__name__)

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


def _infer_structure_flags(prd_markdown: str) -> Tuple[bool, bool]:
    text = (prd_markdown or '').lower()
    backend = any(keyword in text for keyword in ('backend', 'api', 'server', 'database', 'auth', 'crud'))
    frontend = any(keyword in text for keyword in ('frontend', 'ui', 'component', 'page', 'react', 'dashboard'))
    if not backend and not frontend:
        backend = True
        frontend = True
    return backend, frontend


def _coerce_description(payload: Dict[str, str]) -> str:
    description = payload.get('description') or ''
    if description:
        return description
    for key in ('context', 'details', 'summary'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ''


def generate_tickets_from_prd(prd_markdown: str, project_structure: Optional[Dict] = None) -> List[Dict]:
    """
    Generate hierarchical tickets using the BA/Master/Frontend/Backend PM agents.
    Matches the pattern from agentLoop/build.py.
    """
    has_backend: bool
    has_frontend: bool
    if project_structure:
        has_backend = bool(project_structure.get('has_backend', True))
        has_frontend = bool(project_structure.get('has_frontend', True))
        structure_summary = ProjectInitializer.get_structure_summary(project_structure)
    else:
        has_backend, has_frontend = _infer_structure_flags(prd_markdown)
        structure_dict = ProjectInitializer.get_project_structure(has_backend, has_frontend)
        structure_summary = ProjectInitializer.get_structure_summary(structure_dict)

    # Step 1: Master PM creates functional epics
    master_pm = MasterPMAgent()
    master_pm.project_structure = structure_summary
    
    logger.info("Master PM creating functional epics")
    functional_epics = master_pm.generate_functional_epics(prd_markdown)
    if not functional_epics:
        logger.warning("No functional epics generated, falling back to legacy PM agent")
        # Fallback to legacy PM agent to avoid returning no tickets.
        pm_agent = PMAgent()
        return pm_agent.generate_tickets(prd_markdown, project_structure=project_structure)

    logger.info(f"Generated {len(functional_epics)} functional epics")

    # Step 2: Initialize PM agents for frontend and backend
    frontend_pm = FrontendPMAgent()
    frontend_pm.project_structure = structure_summary
    backend_pm = BackendPMAgent()
    backend_pm.project_structure = structure_summary

    tickets: List[Dict[str, object]] = []

    def next_id(prefix: str) -> str:
        return f'{prefix}-{uuid.uuid4()}'

    # Step 3: Process each functional epic
    for functional_epic in functional_epics:
        func_id = str(functional_epic.get('id') or next_id('func'))
        func_epic_title = functional_epic.get('title', 'Functional Epic')
        
        logger.info(f"Processing functional epic: {func_epic_title}")
        
        # Create functional epic ticket
        tickets.append(
            {
                'id': func_id,
                'type': 'epic',
                'title': func_epic_title,
                'description': _coerce_description(functional_epic),
                'status': 'todo',
                'assigned_to': functional_epic.get('assigned_to', 'Master PM') or 'Master PM',
                'parent_id': None,
                'dependencies': [],
            }
        )

        backend_epic_id: Optional[str] = None
        
        # Generate backend epic and stories
        if has_backend:
            logger.info(f"  Backend PM creating epic and stories for: {func_epic_title}")
            backend_result = backend_pm.generate_backend_epic_and_stories(functional_epic, prd_markdown)
            backend_epic = backend_result.get('epic')
            if backend_epic:
                backend_epic_id = next_id('backend')
                tickets.append(
                    {
                        'id': backend_epic_id,
                        'type': 'epic',
                        'title': backend_epic.get('title', 'Backend Epic'),
                        'description': _coerce_description(backend_epic),
                        'status': 'todo',
                        'assigned_to': backend_epic.get('assigned_to', 'Backend Dev') or 'Backend Dev',
                        'parent_id': func_id,
                        'dependencies': [],
                    }
                )
                logger.info(f"    Created BACKEND EPIC: {backend_epic.get('title')}")
                
                # Create backend stories
                for story in backend_result.get('stories', []):
                    tickets.append(
                        {
                            'id': next_id('backend-story'),
                            'type': 'story',
                            'title': story.get('title', 'Backend Story'),
                            'description': _coerce_description(story),
                            'status': story.get('status', 'todo') or 'todo',
                            'assigned_to': story.get('assigned_to', 'Backend Dev') or 'Backend Dev',
                            'parent_id': backend_epic_id,
                            'dependencies': [],
                        }
                    )
                logger.info(f"    Created {len(backend_result.get('stories', []))} backend stories")

        # Generate frontend epic and stories
        if has_frontend:
            logger.info(f"  Frontend PM creating epic and stories for: {func_epic_title}")
            frontend_result = frontend_pm.generate_frontend_epic_and_stories(functional_epic, prd_markdown)
            frontend_epic = frontend_result.get('epic')
            if frontend_epic:
                frontend_epic_id = next_id('frontend')
                # Frontend epic depends on backend epic if it exists
                dependencies = [backend_epic_id] if backend_epic_id else []
                tickets.append(
                    {
                        'id': frontend_epic_id,
                        'type': 'epic',
                        'title': frontend_epic.get('title', 'Frontend Epic'),
                        'description': _coerce_description(frontend_epic),
                        'status': 'todo',
                        'assigned_to': frontend_epic.get('assigned_to', 'Frontend Dev') or 'Frontend Dev',
                        'parent_id': func_id,
                        'dependencies': dependencies,
                    }
                )
                logger.info(f"    Created FRONTEND EPIC: {frontend_epic.get('title')}")
                
                # Create frontend stories
                for story in frontend_result.get('stories', []):
                    tickets.append(
                        {
                            'id': next_id('frontend-story'),
                            'type': 'story',
                            'title': story.get('title', 'Frontend Story'),
                            'description': _coerce_description(story),
                            'status': story.get('status', 'todo') or 'todo',
                            'assigned_to': story.get('assigned_to', 'Frontend Dev') or 'Frontend Dev',
                            'parent_id': frontend_epic_id,
                            'dependencies': [],
                        }
                    )
                logger.info(f"    Created {len(frontend_result.get('stories', []))} frontend stories")

    logger.info(f"Generated {len(tickets)} total tickets")
    return tickets


def summarize_followup_requirements(raw_text: str) -> str:
    """
    Use the BA agent to produce a forgiving summary for continuation requests.
    """
    raw_text = (raw_text or '').strip()
    if not raw_text:
        raise ValueError('Continuation text cannot be empty.')

    ba_agent = BAAgent()
    prompt = (
        "We're continuing work on an existing project. The user wants to add the following:\n"
        f"\"{raw_text}\"\n\n"
        "Clarify the intent and, if you have enough information, respond with a summary starting "
        "with 'REQUIREMENTS_SUMMARY:'. Be forgiving of vague or partial descriptions."
    )
    try:
        response = ba_agent.get_response(prompt)
    except Exception as exc:  # pragma: no cover - OpenAI/transient issues
        logger.exception('BA agent failed to summarize continuation request: %s', exc)
        return raw_text
    summary = _extract_summary_from_response(response)
    if summary:
        return summary

    try:
        fallback = ba_agent.get_response(
            "Please summarize the continuation request so engineering can proceed. "
            "Respond starting with 'REQUIREMENTS_SUMMARY:'."
        )
    except Exception as exc:  # pragma: no cover
        logger.exception('BA agent failed on fallback summary: %s', exc)
        return raw_text
    summary = _extract_summary_from_response(fallback)
    if summary:
        return summary
    return (fallback or response).strip()


def _extract_summary_from_response(text: str) -> str:
    if not text:
        return ''
    marker = 'REQUIREMENTS_SUMMARY:'
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return ''


def run_ticket_builder(job_id: str, callbacks: Optional[object] = None):
    return agent_run_ticket_builder(job_id=job_id, callbacks=callbacks)

