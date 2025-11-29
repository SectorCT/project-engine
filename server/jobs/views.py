import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .artifact_service import FileContentError, FileStructureError, get_file_structure, read_file
from .docker_utils import ContainerNotFound, start_container, stop_container
from .models import App, Job, JobMessage, Ticket
from .serializers import (
    AppSerializer,
    JobContinueSerializer,
    JobCreateSerializer,
    JobDetailSerializer,
    JobMessageCreateSerializer,
    JobMessageSerializer,
    JobSerializer,
    JobUpdateSerializer,
    TicketSerializer,
    TicketWriteSerializer,
)
from .services import (
    finalize_requirements,
    initialize_requirements_collection,
    mark_continuation_enqueued,
    record_chat_message,
    record_description,
)
from .tasks import continue_job_task, run_job_task


logger = logging.getLogger(__name__)


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
        try:
            stop_container(str(instance.id))
        except Exception:  # pragma: no cover - best effort cleanup
            logger.warning('Failed to stop container for job %s during delete', instance.id, exc_info=True)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('delete',), url_path='purge')
    def purge(self, request):
        if not getattr(settings, 'ALLOW_JOB_PURGE', settings.DEBUG):
            return Response({'detail': 'Job purge disabled'}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = Job.objects.filter(owner=request.user).delete()
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)

    def _artifact_error_response(self, exc: Exception):
        kind = getattr(exc, 'kind', 'error')
        if kind == 'not_found':
            status_code = status.HTTP_404_NOT_FOUND
        elif kind == 'not_running':
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({'detail': str(exc)}, status=status_code)

    @action(detail=True, methods=('get',), url_path='files/structure')
    def file_structure(self, request, id=None):
        job = self.get_object()
        path = request.query_params.get('path', '/app')
        try:
            limit = int(request.query_params.get('limit', '200'))
        except ValueError:
            return Response({'detail': 'Query parameter "limit" must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        limit = max(1, min(1000, limit))
        try:
            structure = get_file_structure(str(job.id), path=path, limit=limit)
        except FileStructureError as exc:
            return self._artifact_error_response(exc)
        return Response({'structure': structure})

    @action(detail=True, methods=('get',), url_path='files/content')
    def file_content(self, request, id=None):
        job = self.get_object()
        path = request.query_params.get('path')
        if not path:
            return Response({'detail': 'Query parameter "path" is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = read_file(str(job.id), path)
        except FileContentError as exc:
            return self._artifact_error_response(exc)
        return Response(payload)

    @action(detail=True, methods=('post',), url_path='containers/start')
    def start_container(self, request, id=None):
        job = self.get_object()
        try:
            start_container(str(job.id))
        except ContainerNotFound:
            return Response({'detail': 'Job container not found. The job may need to be rebuilt.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception('Failed to start container for job %s: %s', job.id, exc)
            return Response({'detail': 'Unable to start job container.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'detail': 'Job container is running.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=('post',), url_path='containers/stop')
    def stop_container_action(self, request, id=None):
        job = self.get_object()
        try:
            stop_container(str(job.id))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception('Failed to stop container for job %s: %s', job.id, exc)
            return Response({'detail': 'Unable to stop job container.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'detail': 'Job container stopped.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=('post',), url_path='continue')
    def continue_job(self, request, id=None):
        job = self.get_object()
        serializer = JobContinueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        busy_statuses = {
            Job.Status.COLLECTING,
            Job.Status.QUEUED,
            Job.Status.PLANNING,
            Job.Status.TICKETING,
            Job.Status.BUILDING,
        }
        if job.status in busy_statuses:
            return Response(
                {'detail': 'Job is currently running and cannot be continued yet.'},
                status=status.HTTP_409_CONFLICT,
            )

        if not mark_continuation_enqueued(job):
            return Response(
                {'detail': 'A continuation request is already in progress for this job.'},
                status=status.HTTP_409_CONFLICT,
            )

        continue_job_task.delay(str(job.id), serializer.validated_data['requirements'])
        return Response({'detail': 'Continuation queued.'}, status=status.HTTP_202_ACCEPTED)

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
        metadata = serializer.validated_data.get('metadata')
        if metadata and metadata.get('type') == 'description':
            record_description(
                job,
                agent=serializer.validated_data.get('sender') or 'system',
                stage=metadata.get('stage', ''),
                message=serializer.validated_data['content'],
            )
            return
        record_chat_message(
            job,
            role=serializer.validated_data['role'],
            sender=serializer.validated_data.get('sender', ''),
            content=serializer.validated_data['content'],
            metadata=metadata,
        )


class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Ticket.objects.filter(job__owner=self.request.user).select_related('job', 'parent').prefetch_related('dependencies')
        job_id = self.request.query_params.get('job_id') or self.request.query_params.get('job')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        return queryset.order_by('created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TicketWriteSerializer
        return TicketSerializer

    LOCKED_STATUSES = {
        Job.Status.COLLECTING,
        Job.Status.QUEUED,
        Job.Status.PLANNING,
        Job.Status.TICKETING,
        Job.Status.BUILDING,
    }

    def _ensure_mutable(self, job: Job) -> None:
        if job.status in self.LOCKED_STATUSES:
            raise ValidationError('Tickets cannot be modified while the job is running.')

    def perform_create(self, serializer):
        job = serializer.context['job']
        self._ensure_mutable(job)
        serializer.save()

    def perform_update(self, serializer):
        job = serializer.instance.job
        self._ensure_mutable(job)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_mutable(instance.job)
        instance.delete()
