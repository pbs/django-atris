# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('atris', '0002_historicalrecord_history_diff'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalrecord',
            name='history_date',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalrecord',
            name='object_id',
            field=models.PositiveIntegerField(db_index=True),
        ),
    ]
