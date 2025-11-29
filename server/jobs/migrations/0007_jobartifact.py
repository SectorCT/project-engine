from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_job_build_phase_statuses'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobArtifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=1024)),
                ('type', models.CharField(choices=[('file', 'File'), ('dir', 'Directory')], default='file', max_length=8)),
                ('size', models.BigIntegerField(default=0)),
                ('modified_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='jobs.job')),
            ],
            options={
                'ordering': ('path',),
                'unique_together': {('job', 'path')},
            },
        ),
    ]

