import logging

from celery import shared_task

from .agent_client import run_orchestrator
from .models import Job
from .services import (
    JobCallbacks,
    TicketBuildCallbacks,
    clear_continuation_flag,
    fail_job,
    run_continuation_pipeline,
    set_job_status,
)
from .agent_loop_bridge import run_ticket_builder

logger = logging.getLogger(__name__)


@shared_task
def run_job_task(job_id: str) -> None:
    """Entry point for executing a multi-agent build job."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.warning('Job %s no longer exists. Skipping task.', job_id)
        return

    if job.status == Job.Status.COLLECTING:
        logger.info('Job %s is still collecting requirements; task will be re-triggered later.', job_id)
        return

    # Check if job is paused
    if job.is_paused:
        logger.info('Job %s is paused. Exiting task. Resume to continue.', job_id)
        return

    callbacks = JobCallbacks(job_id=str(job.id))

    # Ensure the job status switches to planning before the orchestrator does work.
    set_job_status(str(job.id), Job.Status.PLANNING, 'Executive planning started')

    # Check pause again after status update
    job.refresh_from_db()
    if job.is_paused:
        logger.info('Job %s was paused during status update. Exiting task.', job_id)
        return

    try:
        run_orchestrator(
            job_id=str(job.id),
            prompt=job.prompt,
            callbacks=callbacks,
            metadata={'user_id': job.owner_id},
        )
    except Exception as exc:  # pragma: no cover - defensive logging path
        message = f'Multi-agent orchestrator failed: {exc}'
        fail_job(str(job.id), message=message)
        logger.exception(message)
        raise


@shared_task
def run_ticket_builder_task(job_id: str) -> None:
    """Execute the build phase by iterating over generated tickets."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.warning('Job %s missing for builder task.', job_id)
        return

    if job.status not in {Job.Status.TICKETS_READY, Job.Status.BUILDING}:
        logger.info('Job %s not in builder-ready state (%s). Skipping.', job_id, job.status)
        return

    # Check if job is paused
    if job.is_paused:
        logger.info('Job %s is paused. Exiting builder task. Resume to continue.', job_id)
        return

    set_job_status(str(job.id), Job.Status.BUILDING, 'Executing tickets')
    
    # Check pause again after status update
    job.refresh_from_db()
    if job.is_paused:
        logger.info('Job %s was paused during status update. Exiting builder task.', job_id)
        return

    callbacks = TicketBuildCallbacks(job_id=str(job.id))

    try:
        run_ticket_builder(job_id=str(job.id), callbacks=callbacks)
    except Exception as exc:  # pragma: no cover
        logger.exception('Ticket builder failed for job %s: %s', job_id, exc)
        callbacks.on_error(f'Ticket execution failed: {exc}')


@shared_task
def continue_job_task(job_id: str, continuation_text: str) -> None:
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.warning('Continuation requested for missing job %s', job_id)
        return

    # Check if job is paused
    if job.is_paused:
        logger.info('Job %s is paused. Exiting continuation task. Resume to continue.', job_id)
        return

    callbacks = JobCallbacks(job_id=str(job.id))
    try:
        run_continuation_pipeline(job, continuation_text, callbacks)
    except Exception as exc:  # pragma: no cover
        message = f'Continuation pipeline failed: {exc}'
        logger.exception(message)
        fail_job(str(job.id), message=message)
        raise
    finally:
        try:
            clear_continuation_flag(str(job.id))
        except Exception:  # pragma: no cover - best effort cleanup
            logger.warning('Failed to clear continuation flag for job %s', job.id)

