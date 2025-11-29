import uuid

from django.conf import settings
from django.db import models


class Job(models.Model):
    """Represents an asynchronous build job owned by a user."""

    class Status(models.TextChoices):
        COLLECTING = 'collecting', 'Collecting Requirements'
        QUEUED = 'queued', 'Queued'
        PLANNING = 'planning', 'Executive Planning'
        PRD_READY = 'prd_ready', 'PRD Ready'
        TICKETING = 'ticketing', 'Generating Tickets'
        TICKETS_READY = 'tickets_ready', 'Tickets Ready'
        BUILDING = 'building', 'Executing Tickets'
        BUILD_DONE = 'build_done', 'Build Complete'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jobs',
    )
    initial_prompt = models.TextField()
    prompt = models.TextField(help_text='Latest refined requirements specification.')
    requirements_summary = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.COLLECTING,
    )
    error_message = models.TextField(blank=True, default='')
    conversation_state = models.JSONField(default=dict, blank=True)
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
    prd_markdown = models.TextField(blank=True, default='')
    prd_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'App for job {self.job_id}'


class JobMessage(models.Model):
    """Chat transcript shared between the user and the agents."""

    class Role(models.TextChoices):
        USER = 'user', 'User'
        AGENT = 'agent', 'Agent'
        SYSTEM = 'system', 'System'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=Role.choices)
    sender = models.CharField(max_length=128, blank=True, default='')
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self) -> str:
        return f'{self.role} message for {self.job_id}'


class Ticket(models.Model):
    class Type(models.TextChoices):
        EPIC = 'epic', 'Epic'
        STORY = 'story', 'Story'
        TASK = 'task', 'Task'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='tickets')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.STORY)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=32, default='todo')
    assigned_to = models.CharField(max_length=128, blank=True, default='Unassigned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dependencies = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependents')

    class Meta:
        ordering = ('created_at',)

    def __str__(self) -> str:
        return f'{self.title} ({self.type})'

