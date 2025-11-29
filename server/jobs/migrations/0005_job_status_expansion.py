from django.db import migrations, models


NEW_CHOICES = [
    ('collecting', 'Collecting Requirements'),
    ('queued', 'Queued'),
    ('planning', 'Executive Planning'),
    ('prd_ready', 'PRD Ready'),
    ('ticketing', 'Generating Tickets'),
    ('tickets_ready', 'Tickets Ready'),
    ('failed', 'Failed'),
]

OLD_CHOICES = [
    ('collecting', 'Collecting Requirements'),
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('done', 'Done'),
    ('failed', 'Failed'),
]


def forwards_status(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(status='running').update(status='planning')
    Job.objects.filter(status='done').update(status='tickets_ready')


def backwards_status(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(status='planning').update(status='running')
    Job.objects.filter(status='prd_ready').update(status='done')
    Job.objects.filter(status='ticketing').update(status='running')
    Job.objects.filter(status='tickets_ready').update(status='done')


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_app_prd_fields'),
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

