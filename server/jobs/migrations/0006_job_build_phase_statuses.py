from django.db import migrations, models


NEW_CHOICES = [
    ('collecting', 'Collecting Requirements'),
    ('queued', 'Queued'),
    ('planning', 'Executive Planning'),
    ('prd_ready', 'PRD Ready'),
    ('ticketing', 'Generating Tickets'),
    ('tickets_ready', 'Tickets Ready'),
    ('building', 'Executing Tickets'),
    ('build_done', 'Build Complete'),
    ('failed', 'Failed'),
]

OLD_CHOICES = [
    ('collecting', 'Collecting Requirements'),
    ('queued', 'Queued'),
    ('planning', 'Executive Planning'),
    ('prd_ready', 'PRD Ready'),
    ('ticketing', 'Generating Tickets'),
    ('tickets_ready', 'Tickets Ready'),
    ('failed', 'Failed'),
]


def forwards_status(apps, schema_editor):
    # No data migration needed; new statuses will be assigned going forward.
    pass


def backwards_status(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(status='building').update(status='tickets_ready')
    Job.objects.filter(status='build_done').update(status='tickets_ready')


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0005_job_status_expansion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(
                choices=NEW_CHOICES,
                default='collecting',
                max_length=32,
            ),
        ),
        migrations.RunPython(forwards_status, backwards_status),
    ]

