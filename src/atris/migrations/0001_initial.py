# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore
from django.contrib.postgres.operations import HStoreExtension


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name='HistoricalRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('history_date', models.DateTimeField(auto_now_add=True)),
                ('history_user', models.CharField(max_length=50, null=True)),
                ('history_user_id', models.PositiveIntegerField(null=True)),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Create'), ('~', 'Update'), ('-', 'Delete')])),
                ('data', django.contrib.postgres.fields.hstore.HStoreField()),
                ('additional_data', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ['-history_date'],
            },
        ),
    ]
