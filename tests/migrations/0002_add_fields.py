from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='episode',
            name='is_published',
            field=models.BooleanField(
                default=True,
                null=False,
            ),
        ),
        migrations.AddField(
            model_name='episode',
            name='keywords',
            field=ArrayField(
                base_field=models.CharField(max_length=20, blank=True),
                null=False,
                default=lambda: [],
            ),
        ),
        migrations.AddField(
            model_name='episode',
            name='episode_metadata',
            field=JSONField(
                null=False,
                default=lambda: {},
            ),
        ),
    ]
