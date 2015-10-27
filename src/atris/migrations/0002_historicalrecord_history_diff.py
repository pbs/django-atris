# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('atris', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalrecord',
            name='history_diff',
            field=django.contrib.postgres.fields.ArrayField(size=None, null=True, base_field=models.CharField(max_length=200), blank=True),
        ),
    ]
