import uuid

from django.conf import settings
from django.db import models


class Job(models.Model):
    """Represents an asynchronous build job owned by a user."""

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jobs',
    )
    prompt = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Job {self.id} ({self.status})'


class JobStep(models.Model):
    """Individual step emitted by one of the multi-agent participants."""

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='steps',
    )
    agent_name = models.CharField(max_length=128)
    message = models.TextField()
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('order', 'created_at')
        unique_together = ('job', 'order')

    def __str__(self) -> str:
        return f'{self.agent_name} #{self.order} for {self.job_id}'


class App(models.Model):
    """Final app artifact produced by a job."""

    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name='app',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='apps',
    )
    spec = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'App for job {self.job_id}'

