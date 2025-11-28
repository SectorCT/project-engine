import logging

from celery import shared_task

from .agent_client import run_orchestrator
from .models import Job
from .services import JobCallbacks, fail_job, set_job_status

logger = logging.getLogger(__name__)


@shared_task
def run_job_task(job_id: str) -> None:
    """Entry point for executing a multi-agent build job."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.warning('Job %s no longer exists. Skipping task.', job_id)
        return

    callbacks = JobCallbacks(job_id=str(job.id))

    # Ensure the job status switches to running before the orchestrator does work.
    set_job_status(str(job.id), Job.Status.RUNNING, 'Job started')

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

