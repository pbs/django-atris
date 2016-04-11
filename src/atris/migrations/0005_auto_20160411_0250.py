# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atris', '0004_archivedhistoricalrecord'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivedhistoricalrecord',
            name='history_type',
            field=models.CharField(db_index=True, max_length=1, choices=[('+', 'Create'), ('~', 'Update'), ('-', 'Delete')]),
        ),
        migrations.AlterField(
            model_name='historicalrecord',
            name='history_type',
            field=models.CharField(db_index=True, max_length=1, choices=[('+', 'Create'), ('~', 'Update'), ('-', 'Delete')]),
        ),
    ]
