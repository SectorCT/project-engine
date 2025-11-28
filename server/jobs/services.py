from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .agent_loop_bridge import (
    force_requirements_summary,
    handle_requirements_message,
    run_executive_flow,
    start_requirements_session,
)
from .models import App, Job, JobMessage, JobStep

logger = logging.getLogger(__name__)


def job_group_name(job_id: str) -> str:
    return f'job_{job_id}'


def broadcast_job_event(job_id: str, payload: Dict[str, Any]) -> None:
    """Send a payload to every websocket listening to the job group."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug('No channel layer configured; skipping broadcast for %s', job_id)
        return

    async_to_sync(channel_layer.group_send)(
        job_group_name(job_id),
        {
            'type': 'job.message',
            'payload': payload,
        },
    )


def set_job_status(job_id: str, status: str, message: Optional[str] = None) -> Job:
    with transaction.atomic():
        job = Job.objects.select_for_update().get(id=job_id)
        job.status = status
        if status == Job.Status.FAILED and message:
            job.error_message = message
        elif status != Job.Status.FAILED:
            job.error_message = ''
        job.save(update_fields=['status', 'error_message', 'updated_at'])

    broadcast_job_event(
        str(job.id),
        {
            'kind': 'status',
            'jobId': str(job.id),
            'status': job.status,
            'message': message or job.error_message,
            'timestamp': timezone.now().isoformat(),
        },
    )
    return job


def append_step(job_id: str, *, agent_name: str, message: str, order: Optional[int] = None) -> JobStep:
    with transaction.atomic():
        job = Job.objects.select_for_update().get(id=job_id)
        if order is None:
            last_order = (
                JobStep.objects.filter(job=job).aggregate(value=Max('order')).get('value') or 0
            )
            order = last_order + 1

        step = JobStep.objects.create(
            job=job,
            agent_name=agent_name,
            message=message,
            order=order,
        )

    broadcast_job_event(
        job_id,
        {
            'kind': 'step',
            'jobId': job_id,
            'agent': step.agent_name,
            'message': step.message,
            'order': step.order,
            'timestamp': step.created_at.isoformat(),
        },
    )
    return step


def store_app(job_id: str, spec: Dict[str, Any]) -> App:
    with transaction.atomic():
        job = Job.objects.select_for_update().select_related('owner').get(id=job_id)
        app, _ = App.objects.update_or_create(
            job=job,
            defaults={
                'owner': job.owner,
                'spec': spec,
            },
        )
        job.status = Job.Status.DONE
        job.error_message = ''
        job.save(update_fields=['status', 'error_message', 'updated_at'])

    broadcast_job_event(
        job_id,
        {
            'kind': 'app',
            'jobId': job_id,
            'status': job.status,
            'spec': app.spec,
            'timestamp': app.updated_at.isoformat(),
        },
    )
    return app


def fail_job(job_id: str, *, message: str) -> Job:
    logger.error('Marking job %s as failed: %s', job_id, message)
    return set_job_status(job_id, Job.Status.FAILED, message)


def initialize_requirements_collection(job: Job) -> Dict[str, Any]:
    """Kick off the requirements gathering agent and store the first response."""
    user_sender = job.owner.name or job.owner.email
    record_chat_message(job, role=JobMessage.Role.USER, sender=user_sender, content=job.initial_prompt)

    response = start_requirements_session(job.initial_prompt, state=_get_requirements_state(job))
    _store_requirements_state(job, response['state'])
    agent_message = response['message']
    record_chat_message(
        job,
        role=JobMessage.Role.AGENT,
        sender=response['agent_name'],
        content=agent_message,
        metadata={'stage': 'requirements'},
    )
    return response


def handle_requirements_chat(job: Job, user_message: str) -> Dict[str, Any]:
    record_chat_message(
        job,
        role=JobMessage.Role.USER,
        sender=job.owner.name or job.owner.email,
        content=user_message,
    )

    state = _get_requirements_state(job)
    response = handle_requirements_message(user_message, state)
    _store_requirements_state(job, response['state'])
    record_chat_message(
        job,
        role=JobMessage.Role.AGENT,
        sender=response['agent_name'],
        content=response['message'],
        metadata={'stage': 'requirements'},
    )
    return response


def force_requirements_completion(job: Job) -> Dict[str, Any]:
    response = force_requirements_summary(_get_requirements_state(job))
    _store_requirements_state(job, response['state'])
    record_chat_message(
        job,
        role=JobMessage.Role.AGENT,
        sender=response['agent_name'],
        content=response['message'],
        metadata={'stage': 'requirements'},
    )
    return response


def finalize_requirements(job: Job, summary: str) -> Job:
    job.prompt = summary
    job.requirements_summary = summary
    state = job.conversation_state or {}
    state['phase'] = 'build_pending'
    job.conversation_state = state
    job.status = Job.Status.QUEUED
    job.save(update_fields=['prompt', 'requirements_summary', 'conversation_state', 'status', 'updated_at'])
    set_job_status(str(job.id), Job.Status.QUEUED, 'Requirements finalized')
    return job


def run_executive_pipeline(job: Job, callbacks: 'JobCallbacks') -> None:
    """Execute the remaining agentLoop phases once requirements are known."""
    history = run_executive_flow(job.prompt)
    for idx, entry in enumerate(history, start=1):
        callbacks.on_step(agent_name=entry['agent'], message=entry['content'], order=idx)

    summary_content = _extract_summary(history)
    spec = {
        'requirements': job.requirements_summary or job.prompt,
        'discussion': history,
        'summary': summary_content,
    }
    callbacks.on_app(spec)


def _extract_summary(history: Any) -> str:
    summary_content = ''
    for entry in reversed(history):
        if entry.get('agent') == 'Secretary':
            summary_content = entry.get('content', '')
            break
    return summary_content


def _get_requirements_state(job: Job) -> Dict[str, Any]:
    return (job.conversation_state or {}).get('requirements', {})


def _store_requirements_state(job: Job, state: Dict[str, Any]) -> None:
    conversation_state = job.conversation_state or {}
    conversation_state['requirements'] = state
    conversation_state['phase'] = 'requirements'
    Job.objects.filter(id=job.id).update(conversation_state=conversation_state, updated_at=timezone.now())


def record_chat_message(
    job: Job,
    *,
    role: str,
    content: str,
    sender: str = '',
    metadata: Optional[Dict[str, Any]] = None,
) -> JobMessage:
    metadata = metadata or {}
    message = JobMessage.objects.create(
        job=job,
        role=role,
        sender=sender,
        content=content,
        metadata=metadata,
    )

    broadcast_job_event(
        str(job.id),
        {
            'kind': 'chat',
            'jobId': str(job.id),
            'role': message.role,
            'sender': sender,
            'content': content,
            'metadata': metadata,
            'timestamp': message.created_at.isoformat(),
        },
    )
    return message


@dataclass
class JobCallbacks:
    """Adapter passed to the orchestrator to mutate state safely."""

    job_id: str

    Status = Job.Status

    def on_status(self, status: str, message: Optional[str] = None) -> None:
        if status not in Job.Status.values:
            raise ValueError(f'Invalid job status "{status}"')
        set_job_status(self.job_id, status, message)

    def on_step(self, *, agent_name: str, message: str, order: Optional[int] = None) -> None:
        append_step(self.job_id, agent_name=agent_name, message=message, order=order)

    def on_app(self, spec: Dict[str, Any]) -> None:
        store_app(self.job_id, spec)

    def on_error(self, message: str) -> None:
        fail_job(self.job_id, message=message)

    def on_chat(self, *, role: str, sender: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        job = Job.objects.get(id=self.job_id)
        record_chat_message(
            job,
            role=role,
            sender=sender,
            content=content,
            metadata=metadata,
        )

