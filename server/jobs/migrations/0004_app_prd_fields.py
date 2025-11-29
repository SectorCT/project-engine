from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_ticket'),
    ]

    operations = [
        migrations.AddField(
            model_name='app',
            name='prd_markdown',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='app',
            name='prd_generated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

