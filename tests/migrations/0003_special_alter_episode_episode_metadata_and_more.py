# Generated by Django 4.2.6 on 2023-10-16 11:46

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0002_add_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Special',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('tests.episode',),
        ),
        migrations.AlterField(
            model_name='episode',
            name='episode_metadata',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='episode',
            name='keywords',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=20), default=list, size=None),
        ),
        migrations.AlterField(
            model_name='episode',
            name='show',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='specials', to='tests.show'),
        ),
        migrations.AlterField(
            model_name='episode2',
            name='episode_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tests.episode'),
        ),
        migrations.AlterField(
            model_name='poll',
            name='custom_id',
            field=models.AutoField(primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='voter',
            name='groups',
            field=models.ManyToManyField(related_name='voters', to='tests.group'),
        ),
    ]
