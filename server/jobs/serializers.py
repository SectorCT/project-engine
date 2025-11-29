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


class JobContinueSerializer(serializers.Serializer):
    requirements = serializers.CharField(max_length=5000, allow_blank=False, trim_whitespace=True)


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


class TicketWriteSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(write_only=True, required=False)
    parent_id = serializers.UUIDField(write_only=True, allow_null=True, required=False)
    dependency_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Ticket
        fields = (
            'id',
            'job_id',
            'parent_id',
            'dependency_ids',
            'type',
            'title',
            'description',
            'status',
            'assigned_to',
        )
        read_only_fields = ('id',)

    def _get_request(self):
        request = self.context.get('request')
        if request is None:
            raise RuntimeError('Serializer requires request in context')
        return request

    def _get_job(self, attrs):
        request = self._get_request()
        job = getattr(self.instance, 'job', None)
        job_id = attrs.pop('job_id', None)
        if job is None:
            if not job_id:
                raise serializers.ValidationError({'job_id': 'This field is required.'})
            try:
                job = Job.objects.get(id=job_id, owner=request.user)
            except Job.DoesNotExist as exc:
                raise serializers.ValidationError({'job_id': 'Job not found.'}) from exc
        elif job_id and job_id != str(job.id):
            raise serializers.ValidationError({'job_id': 'Cannot change job for an existing ticket.'})
        return job

    def validate(self, attrs):
        attrs = super().validate(attrs)
        job = self._get_job(attrs)
        self.context['job'] = job

        # Parent handling
        parent_provided = 'parent_id' in self.initial_data
        self.context['parent_provided'] = parent_provided
        parent = None
        parent_id = attrs.pop('parent_id', None)
        if parent_provided and parent_id:
            try:
                parent = Ticket.objects.get(id=parent_id, job=job)
            except Ticket.DoesNotExist as exc:
                raise serializers.ValidationError({'parent_id': 'Parent ticket not found.'}) from exc
        elif parent_provided:
            parent = None
        self.context['parent'] = parent

        # Dependencies handling
        deps_provided = 'dependency_ids' in self.initial_data
        self.context['dependencies_provided'] = deps_provided
        dependencies = []
        dep_ids = attrs.pop('dependency_ids', [])
        if deps_provided:
            for dep_id in dep_ids:
                if not dep_id:
                    continue
                try:
                    dep = Ticket.objects.get(id=dep_id, job=job)
                except Ticket.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {'dependency_ids': f'Ticket {dep_id} not found.'}
                    ) from exc
                dependencies.append(dep)
        self.context['dependencies'] = dependencies
        return attrs

    def create(self, validated_data):
        job = self.context['job']
        parent = self.context.get('parent')
        dependencies = self.context.get('dependencies', [])
        ticket = Ticket.objects.create(job=job, parent=parent, **validated_data)
        if dependencies:
            ticket.dependencies.set(dependencies)
        return ticket

    def update(self, instance, validated_data):
        parent_provided = self.context.get('parent_provided', False)
        parent = self.context.get('parent')
        dependencies_provided = self.context.get('dependencies_provided', False)
        dependencies = self.context.get('dependencies', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if parent_provided:
            instance.parent = parent
        instance.save()

        if dependencies_provided:
            instance.dependencies.set(dependencies)
        return instance

