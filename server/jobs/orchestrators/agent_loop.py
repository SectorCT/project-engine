from ..models import Job
from ..services import run_executive_pipeline


def run_job(job_id, prompt, callbacks, **kwargs):
    job = Job.objects.get(id=job_id)
    run_executive_pipeline(job, callbacks)

