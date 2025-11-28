from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='conversation_state',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='job',
            name='initial_prompt',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='requirements_summary',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='job',
            name='prompt',
            field=models.TextField(help_text='Latest refined requirements specification.'),
        ),
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(
                choices=[
                    ('collecting', 'Collecting Requirements'),
                    ('queued', 'Queued'),
                    ('running', 'Running'),
                    ('done', 'Done'),
                    ('failed', 'Failed'),
                ],
                default='collecting',
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name='JobMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('agent', 'Agent'), ('system', 'System')], max_length=16)),
                ('sender', models.CharField(blank=True, default='', max_length=128)),
                ('content', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'job',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='jobs.job'),
                ),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
    ]

