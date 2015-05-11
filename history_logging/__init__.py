from __future__ import unicode_literals

__version__ = '0.0.1'


def register(
        model, app=None, manager_name='history', records_class=None,
        **records_config):
    from . import models

    if model._meta.db_table not in models.registered_models:
        if records_class is None:
            records_class = models.HistoryLogging
        records = records_class(**records_config)
        records.manager_name = manager_name
        records.module = app and ("%s.models" % app) or model.__module__
        records.finalize(model)
        models.registered_models[model._meta.db_table] = model