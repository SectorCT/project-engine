from rest_framework import serializers

from .models import App, Job, JobMessage, JobStep


class JobMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobMessage
        fields = ('id', 'role', 'sender', 'content', 'metadata', 'created_at')
        read_only_fields = fields


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


class AppSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='job.id', read_only=True)

    class Meta:
        model = App
        fields = ('id', 'job_id', 'spec', 'created_at', 'updated_at')
        read_only_fields = fields

