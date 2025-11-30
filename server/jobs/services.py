from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .agent_loop_bridge import (
    force_requirements_summary,
    generate_tickets_from_prd,
    get_prd_renderer,
    handle_requirements_message,
    run_executive_flow,
    run_ticket_builder,
    start_requirements_session,
    summarize_followup_requirements,
)
from .docker_utils import stop_container
from .models import App, Job, JobMessage, JobStep, Ticket

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


def _cleanup_job_container(job_id: str) -> None:
    if not getattr(settings, 'CLEANUP_JOB_CONTAINERS', True):
        return
    try:
        stop_container(job_id)
    except Exception:  # pragma: no cover - best effort
        logger.warning('Failed to clean up container for job %s', job_id, exc_info=True)


def broadcast_ticket_update(
    ticket: Ticket,
    *,
    status: Optional[str] = None,
    message: str = '',
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        'kind': 'ticketUpdate',
        'jobId': str(ticket.job_id),
        'ticketId': str(ticket.id),
        'status': status or ticket.status,
        'title': ticket.title,
        'type': ticket.type,
        'assignedTo': ticket.assigned_to,
        'message': message,
        'timestamp': timezone.now().isoformat(),
    }
    if extra:
        payload['metadata'] = extra
    broadcast_job_event(str(ticket.job_id), payload)


def set_ticket_status(
    ticket: Ticket,
    *,
    status: str,
    message: str = '',
    extra: Optional[Dict[str, Any]] = None,
) -> Ticket:
    ticket.status = status
    ticket.save(update_fields=['status', 'updated_at'])
    # Refresh to ensure we have the latest data
    ticket.refresh_from_db()
    
    broadcast_ticket_update(ticket, status=status, message=message, extra=extra)
    
    # Also send a chat message to Agent Communication with the assigned dev as sender
    # Ensure we have the latest job instance to avoid stale data
    job = Job.objects.get(id=ticket.job_id)
    assigned_dev = ticket.assigned_to or 'Unassigned'
    status_emoji = {
        'in_progress': '🔄',
        'done': '✅',
        'failed': '❌',
        'todo': '📝',
        'pending': '⏳',
    }.get(status.lower(), '📋')
    
    chat_message = message or f'{status_emoji} Ticket "{ticket.title}" status changed to {status}'
    if message:
        chat_message = f'{status_emoji} {message}'
    
    # Persist the chat message - this must be saved to database for page reloads
    record_chat_message(
        job,
        role='system',
        sender=assigned_dev,
        content=chat_message,
        metadata={
            'ticketId': str(ticket.id),
            'ticketTitle': ticket.title,
            'ticketStatus': status,
            'ticketType': ticket.type,
            **(extra or {}),
        },
        broadcast=True,
    )
    
    return ticket


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
            'kind': 'jobStatus',
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
            'kind': 'agentDialogue',
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

    broadcast_job_event(
        job_id,
        {
            'kind': 'prdReady',
            'jobId': job_id,
            'spec': app.spec,
            'prdMarkdown': app.prd_markdown,
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
    record_chat_message(
        job,
        role=JobMessage.Role.USER,
        sender=user_sender,
        content=job.initial_prompt,
        broadcast=False,
    )

    response = start_requirements_session(job.initial_prompt, state=_get_requirements_state(job))
    _store_requirements_state(job, response['state'])
    agent_message = response['message']
    record_description(
        job,
        agent=response['agent_name'],
        stage='Collecting Requirements',
        message='Client Relations is clarifying the idea.',
    )
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
        broadcast=False,
    )

    state = _get_requirements_state(job)
    response = handle_requirements_message(user_message, state)
    _store_requirements_state(job, response['state'])
    record_description(
        job,
        agent=response['agent_name'],
        stage='Collecting Requirements',
        message='Client Relations is processing the latest answer.',
    )
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
    record_description(
        job,
        agent='Coordinator',
        stage='Queued',
        message='Handing project to executive agents.',
    )
    return job


def run_executive_pipeline(job: Job, callbacks: 'JobCallbacks', requirements_text: Optional[str] = None) -> None:
    """Execute the remaining agentLoop phases once requirements are known."""
    requirements_text = requirements_text or job.prompt
    callbacks.on_status(Job.Status.PLANNING, 'Executive agents are planning the build')
    record_description(
        job,
        agent='Coordinator',
        stage='Executive Planning',
        message='Executive agents are aligning on the implementation plan.',
    )

    history = run_executive_flow(requirements_text)
    for idx, entry in enumerate(history, start=1):
        record_description(
            job,
            agent=entry['agent'],
            stage='Executive Planning',
            message=f'{entry["agent"]} is responding.',
        )
        callbacks.on_step(agent_name=entry['agent'], message=entry['content'], order=idx)

    summary_content = _extract_summary(history)
    prd_renderer = get_prd_renderer()
    prd_content = prd_renderer.render_prd(requirements_text, history, project_name=str(job.id))
    spec = {
        'requirements': requirements_text,
        'discussion': history,
        'summary': summary_content,
    }
    callbacks.on_app(spec)

    job.refresh_from_db()
    if not hasattr(job, 'app'):
        job = Job.objects.select_related('app').get(id=job.id)
    if job.app:
        job.app.prd_markdown = prd_content
        job.app.prd_generated_at = timezone.now()
        job.app.save(update_fields=['prd_markdown', 'prd_generated_at', 'updated_at'])

    callbacks.on_status(Job.Status.PRD_READY, 'PRD ready for ticketing')
    record_description(
        job,
        agent='Coordinator',
        stage='Executive Planning',
        message='PRD is finalized. Preparing ticket breakdown.',
    )

    generate_tickets_for_job(job, callbacks)


def run_continuation_pipeline(job: Job, continuation_text: str, callbacks: 'JobCallbacks') -> None:
    """Re-run the executive/ticketing/build pipeline for follow-up requirements."""
    record_description(
        job,
        agent='Coordinator',
        stage='Continuation',
        message='Processing follow-up request for new requirements.',
    )

    record_chat_message(
        job,
        role=JobMessage.Role.USER,
        sender=job.owner.name or job.owner.email,
        content=continuation_text,
        metadata={'stage': 'continuation', 'type': 'user_followup'},
        broadcast=False,
    )

    try:
        summary = summarize_followup_requirements(continuation_text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception('Failed to summarize continuation for job %s: %s', job.id, exc)
        raise RuntimeError('Failed to summarize continuation request') from exc

    if not summary.strip():
        summary = continuation_text.strip()
    record_chat_message(
        job,
        role=JobMessage.Role.SYSTEM,
        sender='Business Analyst',
        content=f'REQUIREMENTS_SUMMARY: {summary}',
        metadata={'stage': 'continuation', 'type': 'summary'},
    )

    state = job.conversation_state or {}
    if 'initial_summary' not in state and (job.requirements_summary or job.prompt):
        state['initial_summary'] = job.requirements_summary or job.prompt
    history = state.setdefault('continuations', [])
    history.append(
        {
            'requested_at': timezone.now().isoformat(),
            'request': continuation_text,
            'summary': summary,
        }
    )
    state.setdefault('continuation', {}).setdefault('in_progress', True)

    job.prompt = summary
    job.requirements_summary = summary
    job.conversation_state = state
    job.save(update_fields=['prompt', 'requirements_summary', 'conversation_state', 'updated_at'])

    set_job_status(str(job.id), Job.Status.QUEUED, 'Continuation queued')
    run_executive_pipeline(job, callbacks, requirements_text=summary)


def generate_tickets_for_job(job: Job, callbacks: 'JobCallbacks') -> int:
    """Create structured tickets from the PRD and broadcast progress."""
    app = getattr(job, 'app', None)
    if app is None or not app.prd_markdown:
        logger.warning('Job %s missing PRD markdown; skipping ticket generation', job.id)
        return 0

    callbacks.on_status(Job.Status.TICKETING, 'Generating tickets from PRD')
    callbacks.on_description(
        agent='Project Manager',
        stage='Ticket Generation',
        message='Project Manager is breaking the PRD into Epics and Stories.',
    )

    try:
        ticket_payload = generate_tickets_from_prd(app.prd_markdown)
    except Exception as exc:  # pragma: no cover - OpenAI failures, etc.
        logger.exception('Ticket generation failed for job %s: %s', job.id, exc)
        callbacks.on_description(
            agent='Project Manager',
            stage='Ticket Generation',
            message='Ticket generation failed. Please retry later.',
        )
        callbacks.on_error(f'Ticket generation failed: {exc}')
        return 0

    if not ticket_payload:
        callbacks.on_description(
            agent='Project Manager',
            stage='Ticket Generation',
            message='Ticket generator returned no actionable work items.',
        )
        callbacks.on_status(Job.Status.TICKETS_READY, 'No tickets generated')
        return 0

    created = _persist_generated_tickets(job, ticket_payload)
    callbacks.on_description(
        agent='Project Manager',
        stage='Ticket Generation',
        message=f'{created} tickets ready for execution.',
    )
    callbacks.on_status(Job.Status.TICKETS_READY, f'{created} tickets ready')
    from .tasks import run_ticket_builder_task
    run_ticket_builder_task.delay(str(job.id))
    return created


def _extract_summary(history: Any) -> str:
    summary_content = ''
    for entry in reversed(history):
        if entry.get('agent') == 'Secretary':
            summary_content = entry.get('content', '')
            break
    return summary_content


def _persist_generated_tickets(job: Job, tickets_data: List[Dict[str, Any]]) -> int:
    """Persist the PM agent output into the Ticket table with correct relations."""
    if not tickets_data:
        job.tickets.all().delete()
        return 0

    temp_map: Dict[str, Ticket] = {}
    created = 0
    total_tickets = len(tickets_data)

    # Broadcast reset message first
    broadcast_job_event(
        str(job.id),
        {
            'kind': 'ticketReset',
            'jobId': str(job.id),
            'timestamp': timezone.now().isoformat(),
        },
    )

    # Broadcast start message (also send as chat message)
    start_message = f'📋 Creating {total_tickets} ticket{"s" if total_tickets != 1 else ""}...'
    broadcast_job_event(
        str(job.id),
        {
            'kind': 'stageUpdate',
            'jobId': str(job.id),
            'role': 'system',
            'sender': 'Project Manager',
            'content': start_message,
            'timestamp': timezone.now().isoformat(),
        },
    )
    record_chat_message(
        job,
        role='system',
        sender='Project Manager',
        content=start_message,
        metadata={'stage': 'ticket_generation', 'type': 'system_activity'},
        broadcast=True,
    )

    with transaction.atomic():
        job.tickets.all().delete()

        for idx, payload in enumerate(tickets_data):
            temp_id = payload.get('id')
            if temp_id is None:
                temp_id = f'auto-{idx}'
            temp_id = str(temp_id)

            ticket_type = payload.get('type', Ticket.Type.STORY)
            if ticket_type not in Ticket.Type.values:
                ticket_type = Ticket.Type.STORY

            ticket = Ticket.objects.create(
                job=job,
                type=ticket_type,
                title=payload.get('title', 'Untitled Ticket')[:255],
                description=payload.get('description', ''),
                status=payload.get('status', 'todo')[:32],
                assigned_to=payload.get('assigned_to', 'Unassigned') or 'Unassigned',
            )
            temp_map[temp_id] = ticket
            created += 1
            
            # Broadcast each ticket creation immediately (outside transaction for real-time updates)
            # We need to commit the transaction first, but we'll do it after the loop
            # For now, broadcast immediately - Django will handle the transaction
            broadcast_ticket_update(
                ticket,
                status=ticket.status,
                message='Ticket initialized',
                extra={'event': 'created', 'progress': f'{created}/{total_tickets}'},
            )

        for payload in tickets_data:
            temp_id = payload.get('id')
            if temp_id is None:
                continue
            ticket = temp_map.get(str(temp_id))
            if not ticket:
                continue

            parent_id = payload.get('parent_id')
            if parent_id:
                parent = temp_map.get(str(parent_id))
                if parent:
                    ticket.parent = parent
                    ticket.save(update_fields=['parent', 'updated_at'])

            dep_ids = [temp_map[str(dep)] for dep in payload.get('dependencies', []) if str(dep) in temp_map]
            if dep_ids:
                ticket.dependencies.set(dep_ids)

    # Cleanup: Delete epics with no stories
    all_tickets = list(job.tickets.all())
    epics = [t for t in all_tickets if t.type == Ticket.Type.EPIC]
    stories = [t for t in all_tickets if t.type == Ticket.Type.STORY]
    
    # Build a map of epic IDs to story counts
    epic_id_to_story_count = {}
    for story in stories:
        parent_id = story.parent_id
        if parent_id:
            parent_id_str = str(parent_id)
            epic_id_to_story_count[parent_id_str] = epic_id_to_story_count.get(parent_id_str, 0) + 1
    
    # Find and delete epics with no stories
    deleted_count = 0
    for epic in epics:
        epic_id_str = str(epic.id)
        story_count = epic_id_to_story_count.get(epic_id_str, 0)
        
        if story_count == 0:
            logger.debug('Deleting epic %s (%s) - no stories', epic.id, epic.title)
            epic.delete()
            deleted_count += 1
    
    if deleted_count > 0:
        logger.info('Deleted %d epics with no stories for job %s', deleted_count, job.id)

    # Broadcast summary message after all tickets are created (also send as chat message)
    final_count = job.tickets.count()
    if final_count > 0:
        summary_message = f'✅ Created {final_count} ticket{"s" if final_count != 1 else ""} successfully! Ready for execution.'
        broadcast_job_event(
            str(job.id),
            {
                'kind': 'stageUpdate',
                'jobId': str(job.id),
                'role': 'system',
                'sender': 'Project Manager',
                'content': summary_message,
                'timestamp': timezone.now().isoformat(),
            },
        )
        record_chat_message(
            job,
            role='system',
            sender='Project Manager',
            content=summary_message,
            metadata={'stage': 'ticket_generation', 'type': 'system_activity'},
            broadcast=True,
        )

    return created


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
    broadcast: bool = True,
) -> JobMessage:
    metadata = metadata or {}
    # Ensure message is saved immediately (outside any transaction that might rollback)
    # Use get() to ensure we have the latest job instance
    job = Job.objects.get(id=job.id)
    message = JobMessage.objects.create(
        job=job,
        role=role,
        sender=sender,
        content=content,
        metadata=metadata,
    )
    # Force database commit by refreshing from DB
    message.refresh_from_db()

    if broadcast:
        broadcast_job_event(
            str(job.id),
            {
                'kind': 'stageUpdate',
                'jobId': str(job.id),
                'role': message.role,
                'sender': sender,
                'content': content,
                'metadata': metadata,
                'timestamp': message.created_at.isoformat(),
            },
        )
    return message


def record_description(job: Job, *, agent: str, stage: str, message: str) -> JobMessage:
    metadata = {'type': 'description', 'stage': stage, 'agent': agent}
    return record_chat_message(
        job,
        role=JobMessage.Role.SYSTEM,
        sender=agent,
        content=message,
        metadata=metadata,
    )


def mark_continuation_enqueued(job: Job) -> bool:
    """
    Flag a job as having an in-flight continuation request.
    Returns False if another continuation is already running.
    """
    with transaction.atomic():
        locked_job = Job.objects.select_for_update().get(id=job.id)
        state = locked_job.conversation_state or {}
        continuation_meta = state.get('continuation') or {}
        if continuation_meta.get('in_progress'):
            return False
        continuation_meta['in_progress'] = True
        continuation_meta['queued_at'] = timezone.now().isoformat()
        state['continuation'] = continuation_meta
        locked_job.conversation_state = state
        locked_job.save(update_fields=['conversation_state', 'updated_at'])
    return True


def clear_continuation_flag(job_id: str) -> None:
    """Release the continuation in-progress flag (best effort)."""
    with transaction.atomic():
        job = Job.objects.select_for_update().get(id=job_id)
        state = job.conversation_state or {}
        continuation_meta = state.get('continuation') or {}
        continuation_meta.pop('queued_at', None)
        continuation_meta.pop('in_progress', None)
        if continuation_meta:
            state['continuation'] = continuation_meta
        elif 'continuation' in state:
            state.pop('continuation')
        job.conversation_state = state
        job.save(update_fields=['conversation_state', 'updated_at'])


def pause_job(job_id: str) -> Job:
    """
    Pause a running job. Tasks will check this flag and exit gracefully.
    Returns the updated job.
    """
    from django.core.exceptions import FieldError
    from django.db import DatabaseError
    
    with transaction.atomic():
        job = Job.objects.select_for_update().get(id=job_id)
        if not hasattr(job, 'is_paused'):
            raise FieldError('is_paused field does not exist. Migration may not have been applied.')
        if job.is_paused:
            return job  # Already paused
        try:
            job.is_paused = True
            job.save(update_fields=['is_paused', 'updated_at'])
        except (DatabaseError, FieldError) as exc:
            logger.error('Failed to save is_paused field for job %s: %s', job_id, exc)
            raise
    
    broadcast_job_event(
        str(job.id),
        {
            'kind': 'jobStatus',
            'jobId': str(job.id),
            'status': job.status,
            'message': 'Job paused',
            'metadata': {'paused': True},
            'timestamp': timezone.now().isoformat(),
        },
    )
    record_description(
        job,
        agent='Coordinator',
        stage='Paused',
        message='Job execution has been paused. Resume to continue.',
    )
    return job


def resume_job(job_id: str) -> Job:
    """
    Resume a paused job. Re-queues the appropriate task based on current status.
    Returns the updated job.
    """
    from django.core.exceptions import FieldError
    from django.db import DatabaseError
    from .tasks import continue_job_task, run_job_task, run_ticket_builder_task
    
    with transaction.atomic():
        job = Job.objects.select_for_update().get(id=job_id)
        if not hasattr(job, 'is_paused'):
            raise FieldError('is_paused field does not exist. Migration may not have been applied.')
        if not job.is_paused:
            return job  # Not paused
        try:
            job.is_paused = False
            job.save(update_fields=['is_paused', 'updated_at'])
        except (DatabaseError, FieldError) as exc:
            logger.error('Failed to save is_paused field for job %s: %s', job_id, exc)
            raise
    
    broadcast_job_event(
        str(job.id),
        {
            'kind': 'jobStatus',
            'jobId': str(job.id),
            'status': job.status,
            'message': 'Job resumed',
            'metadata': {'paused': False},
            'timestamp': timezone.now().isoformat(),
        },
    )
    record_description(
        job,
        agent='Coordinator',
        stage='Resumed',
        message='Job execution has been resumed. Continuing from current phase.',
    )
    
    # Re-queue the appropriate task based on current status
    if job.status == Job.Status.QUEUED:
        run_job_task.delay(str(job.id))
    elif job.status == Job.Status.TICKETS_READY:
        run_ticket_builder_task.delay(str(job.id))
    elif job.status == Job.Status.BUILDING:
        run_ticket_builder_task.delay(str(job.id))
    # For COLLECTING, PLANNING, TICKETING, the tasks will naturally continue
    # when the current operation completes and checks the pause flag
    
    return job


def check_job_paused(job_id: str) -> bool:
    """Check if a job is currently paused."""
    try:
        job = Job.objects.get(id=job_id)
        return job.is_paused
    except Job.DoesNotExist:
        return False


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

    def on_description(self, *, agent: str, stage: str, message: str) -> None:
        job = Job.objects.get(id=self.job_id)
        record_description(job, agent=agent, stage=stage, message=message)


@dataclass
class TicketBuildCallbacks:
    job_id: str
    _job: Optional[Job] = None
    has_failures: bool = False
    failure_messages: List[str] = field(default_factory=list)

    def _get_job(self) -> Job:
        if self._job is None:
            self._job = Job.objects.get(id=self.job_id)
        return self._job

    def is_paused(self) -> bool:
        """Check if the job is currently paused. Can be called between ticket executions."""
        try:
            job = Job.objects.get(id=self.job_id)
            return job.is_paused
        except Job.DoesNotExist:
            return False

    def on_stage(self, stage: str, message: str) -> None:
        job = self._get_job()
        record_description(job, agent='Builder', stage=stage, message=message)
        # Also send as chat message from devops engineer for system activities
        record_chat_message(
            job,
            role='system',
            sender='devops engineer',
            content=message,
            metadata={'stage': stage, 'type': 'system_activity'},
            broadcast=True,
        )

    def on_ticket_progress(
        self,
        *,
        ticket_id: str,
        status: str,
        message: str = '',
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            ticket = Ticket.objects.get(id=ticket_id, job_id=self.job_id)
        except Ticket.DoesNotExist:
            logger.warning('Ticket %s missing for job %s', ticket_id, self.job_id)
            return
        set_ticket_status(ticket, status=status, message=message, extra=extra)
        if status.lower() == 'failed':
            self.has_failures = True
            failure_detail = message
            if not failure_detail and extra and extra.get('error'):
                failure_detail = extra['error']
            if failure_detail:
                self.failure_messages.append(f"{ticket.title}: {failure_detail}")
            else:
                self.failure_messages.append(ticket.title)

    def on_log(self, message: str) -> None:
        job = self._get_job()
        record_description(job, agent='Builder', stage='Build Execution', message=message)
        # Also send as chat message from devops engineer
        record_chat_message(
            job,
            role='system',
            sender='devops engineer',
            content=message,
            metadata={'stage': 'Build Execution', 'type': 'system_log'},
            broadcast=True,
        )

    def on_error(self, message: str) -> None:
        fail_job(self.job_id, message=message)
        _cleanup_job_container(self.job_id)

    def on_complete(self, message: str = 'Implementation complete') -> None:
        if self.has_failures:
            failure_msg = '; '.join(self.failure_messages) if self.failure_messages else 'One or more tickets failed'
            fail_job(self.job_id, message=failure_msg)
        else:
            set_job_status(self.job_id, Job.Status.BUILD_DONE, message)
        _cleanup_job_container(self.job_id)

