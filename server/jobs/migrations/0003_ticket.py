from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_job_conversation_and_messages'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('epic', 'Epic'), ('story', 'Story'), ('task', 'Task')], default='story', max_length=16)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(default='todo', max_length=32)),
                ('assigned_to', models.CharField(blank=True, default='Unassigned', max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='jobs.job')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='jobs.ticket')),
                ('dependencies', models.ManyToManyField(blank=True, related_name='dependents', to='jobs.ticket')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
    ]

