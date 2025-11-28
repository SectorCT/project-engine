from rest_framework import serializers

from .models import App, Job, JobStep


class JobStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobStep
        fields = ('id', 'agent_name', 'message', 'order', 'created_at')
        read_only_fields = fields


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ('id', 'prompt', 'status', 'error_message', 'created_at', 'updated_at')
        read_only_fields = ('id', 'status', 'error_message', 'created_at', 'updated_at')


class JobDetailSerializer(JobSerializer):
    steps = JobStepSerializer(many=True, read_only=True)

    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + ('steps',)


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

