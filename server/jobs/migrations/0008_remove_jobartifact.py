from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0007_jobartifact'),
    ]

    operations = [
        migrations.DeleteModel(
            name='JobArtifact',
        ),
    ]

