from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0008_remove_jobartifact'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='is_paused',
            field=models.BooleanField(default=False, help_text='When True, job execution is paused and tasks will exit gracefully.'),
        ),
    ]

