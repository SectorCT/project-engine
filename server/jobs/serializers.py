from rest_framework import serializers

from .models import App, Job, JobMessage, JobStep, Ticket


class JobMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobMessage
        fields = ('id', 'role', 'sender', 'content', 'metadata', 'created_at')
        read_only_fields = fields


class JobMessageCreateSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = JobMessage
        fields = ('job_id', 'role', 'sender', 'content', 'metadata')

    def validate_job_id(self, value):
        try:
            job = Job.objects.get(id=value, owner=self.context['request'].user)
        except Job.DoesNotExist as exc:
            raise serializers.ValidationError('Job not found') from exc
        self.context['job'] = job
        return value


class JobStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobStep
        fields = ('id', 'agent_name', 'message', 'order', 'created_at')
        read_only_fields = fields


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            'id',
            'initial_prompt',
            'prompt',
            'requirements_summary',
            'status',
            'error_message',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'initial_prompt',
            'prompt',
            'requirements_summary',
            'status',
            'error_message',
            'created_at',
            'updated_at',
        )


class JobDetailSerializer(JobSerializer):
    steps = JobStepSerializer(many=True, read_only=True)
    messages = JobMessageSerializer(many=True, read_only=True)

    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + ('steps', 'messages')


class JobCreateSerializer(serializers.ModelSerializer):
    prompt = serializers.CharField(max_length=5000)

    class Meta:
        model = Job
        fields = ('prompt',)


class JobUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ('initial_prompt',)


class AppSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='job.id', read_only=True)

    class Meta:
        model = App
        fields = ('id', 'job_id', 'spec', 'prd_markdown', 'prd_generated_at', 'created_at', 'updated_at')
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    parent_id = serializers.UUIDField(source='parent.id', read_only=True)
    dependencies = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = (
            'id',
            'job_id',
            'parent_id',
            'type',
            'title',
            'description',
            'status',
            'assigned_to',
            'dependencies',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_dependencies(self, obj):
        return [str(dep.id) for dep in obj.dependencies.all()]

