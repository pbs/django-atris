# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('atris', '0003_added_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchivedHistoricalRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(db_index=True)),
                ('history_date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('history_user', models.CharField(max_length=50, null=True)),
                ('history_user_id', models.PositiveIntegerField(null=True)),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Create'), ('~', 'Update'), ('-', 'Delete')])),
                ('history_diff', django.contrib.postgres.fields.ArrayField(size=None, null=True, base_field=models.CharField(max_length=200), blank=True)),
                ('data', django.contrib.postgres.fields.hstore.HStoreField()),
                ('additional_data', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ['-history_date'],
                'abstract': False,
            },
        ),
    ]
