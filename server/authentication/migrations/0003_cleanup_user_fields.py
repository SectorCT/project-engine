from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_company_and_user_company_verified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='company',
        ),
        migrations.RemoveField(
            model_name='user',
            name='phoneNumber',
        ),
        migrations.RemoveField(
            model_name='user',
            name='isManager',
        ),
        migrations.RemoveField(
            model_name='user',
            name='verified',
        ),
        migrations.DeleteModel(
            name='Company',
        ),
    ]

