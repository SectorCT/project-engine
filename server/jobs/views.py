from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import App, Job
from django.conf import settings

from .models import App, Job, JobMessage
from .serializers import (
    AppSerializer,
    JobCreateSerializer,
    JobDetailSerializer,
    JobMessageCreateSerializer,
    JobMessageSerializer,
    JobSerializer,
    JobUpdateSerializer,
)
from .services import finalize_requirements, initialize_requirements_collection, record_chat_message
from .tasks import run_job_task


class JobViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    lookup_field = 'id'
    lookup_value_regex = '[0-9a-fA-F-]+'

    def get_queryset(self):
        queryset = Job.objects.filter(owner=self.request.user)
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('steps', 'messages')
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return JobDetailSerializer
        if self.action == 'create':
            return JobCreateSerializer
        if self.action in ('update', 'partial_update'):
            return JobUpdateSerializer
        return JobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        initial_prompt = serializer.validated_data['prompt']
        job = Job.objects.create(
            owner=request.user,
            initial_prompt=initial_prompt,
            prompt=initial_prompt,
        )
        response = initialize_requirements_collection(job)
        if response.get('finished') and response.get('summary'):
            finalize_requirements(job, response['summary'])
            job.refresh_from_db()
            run_job_task.delay(str(job.id))
        output = JobSerializer(job, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        job = serializer.instance
        serializer.save()
        if job.status == Job.Status.COLLECTING:
            job.prompt = job.initial_prompt
            job.save(update_fields=['prompt'])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('delete',), url_path='purge')
    def purge(self, request):
        if not getattr(settings, 'ALLOW_JOB_PURGE', settings.DEBUG):
            return Response({'detail': 'Job purge disabled'}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = Job.objects.filter(owner=request.user).delete()
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)


class AppViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AppSerializer

    def get_queryset(self):
        return App.objects.filter(owner=self.request.user)

    @action(detail=False, methods=('get',), url_path=r'by-job/(?P<job_id>[0-9a-fA-F-]+)')
    def by_job(self, request, job_id=None):
        job = get_object_or_404(Job, id=job_id, owner=request.user)
        app = getattr(job, 'app', None)
        if app is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(app)
        return Response(serializer.data)


class JobMessageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = JobMessage.objects.filter(job__owner=self.request.user).select_related('job')
        job_id = self.request.query_params.get('job_id') or self.request.query_params.get('job')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        return queryset.order_by('created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return JobMessageCreateSerializer
        return JobMessageSerializer

    def perform_create(self, serializer):
        job = serializer.context['job']
        record_chat_message(
            job,
            role=serializer.validated_data['role'],
            sender=serializer.validated_data.get('sender', ''),
            content=serializer.validated_data['content'],
            metadata=serializer.validated_data.get('metadata'),
        )

