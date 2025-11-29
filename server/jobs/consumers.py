import json

from django.core.exceptions import PermissionDenied
from django.db import transaction
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Job
from .services import finalize_requirements, handle_requirements_chat, job_group_name
from .tasks import run_job_task


class JobConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        import logging
        logger = logging.getLogger(__name__)
        
        user = self.scope.get('user')
        if user is None or user.is_anonymous:
            logger.warning(f"WebSocket connection rejected: anonymous user")
            await self.close(code=4001)
            return

        self.job_id = self.scope['url_route']['kwargs']['job_id']
        logger.info(f"WebSocket connection attempt for job {self.job_id} by user {user.id}")
        
        owns_job = await self._user_owns_job(user_id=user.id, job_id=self.job_id)
        if not owns_job:
            logger.warning(f"WebSocket connection rejected: user {user.id} does not own job {self.job_id}")
            await self.close(code=4003)
            return

        self.group_name = job_group_name(self.job_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connection accepted for job {self.job_id} by user {user.id}")

    async def disconnect(self, close_code):
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        
        job_id = getattr(self, 'job_id', 'unknown')
        logger.info(f"WebSocket disconnecting for job {job_id}, close_code: {close_code}")
        
        if hasattr(self, 'group_name'):
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception as e:
                logger.error(f"Error discarding group {self.group_name}: {e}")
        else:
            logger.warning(f"WebSocket disconnecting without group_name, close_code: {close_code}")

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data is None:
            return
        stripped = text_data.strip()
        if not stripped:
            return
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            await self.send_json(
                {
                    'kind': 'error',
                    'message': 'Invalid JSON payload. Expected e.g. {"kind": "chat", "content": "..."}',
                }
            )
            return
        await self.receive_json(payload, **kwargs)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.send_json(
                {
                    'kind': 'error',
                    'message': 'Invalid JSON payload. Expected e.g. {"kind": "chat", "content": "..."}',
                }
            )
            return
        kind = content.get('kind')
        if kind == 'chat':
            message = (content.get('content') or '').strip()
            if not message:
                return
            result = await self._handle_user_chat(self.scope['user'].id, self.job_id, message)
            if result.get('enqueue'):
                run_job_task.delay(self.job_id)

    async def job_message(self, event):
        await self.send_json(event['payload'])

    @database_sync_to_async
    def _user_owns_job(self, *, user_id, job_id):
        return Job.objects.filter(id=job_id, owner_id=user_id).exists()

    @database_sync_to_async
    def _handle_user_chat(self, user_id, job_id, message):
        with transaction.atomic():
            job = Job.objects.select_for_update().get(id=job_id)
            if job.owner_id != user_id:
                raise PermissionDenied('You do not have access to this job')
            if job.status != Job.Status.COLLECTING:
                return {'accepted': False, 'enqueue': False}

            response = handle_requirements_chat(job, message)
            should_enqueue = False
            if response.get('finished') and response.get('summary'):
                finalize_requirements(job, response['summary'])
                should_enqueue = True
            return {'accepted': True, 'enqueue': should_enqueue}

