from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Job
from .services import job_group_name


class JobConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if user is None or user.is_anonymous:
            await self.close(code=4001)
            return

        self.job_id = self.scope['url_route']['kwargs']['job_id']
        owns_job = await self._user_owns_job(user_id=user.id, job_id=self.job_id)
        if not owns_job:
            await self.close(code=4003)
            return

        self.group_name = job_group_name(self.job_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_message(self, event):
        await self.send_json(event['payload'])

    @database_sync_to_async
    def _user_owns_job(self, *, user_id, job_id):
        return Job.objects.filter(id=job_id, owner_id=user_id).exists()

