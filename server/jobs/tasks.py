import logging

from celery import shared_task

from .agent_client import run_orchestrator
from .models import Job
from .services import JobCallbacks, TicketBuildCallbacks, fail_job, set_job_status
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

    callbacks = JobCallbacks(job_id=str(job.id))

    # Ensure the job status switches to planning before the orchestrator does work.
    set_job_status(str(job.id), Job.Status.PLANNING, 'Executive planning started')

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

    set_job_status(str(job.id), Job.Status.BUILDING, 'Executing tickets')
    callbacks = TicketBuildCallbacks(job_id=str(job.id))

    try:
        run_ticket_builder(job_id=str(job.id), callbacks=callbacks)
    except Exception as exc:  # pragma: no cover
        logger.exception('Ticket builder failed for job %s: %s', job_id, exc)
        callbacks.on_error(f'Ticket execution failed: {exc}')

