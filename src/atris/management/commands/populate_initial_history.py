# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from django.utils import six

str = str if six.PY2 else str

from optparse import make_option

from django.core.management import BaseCommand

from atris import models
from atris.models import HistoricalRecord


class Command(BaseCommand):
    EXISTING_HISTORY_FOUND = "Existing history found, skipping model"
    option_list = BaseCommand.option_list + (
        make_option(
            '--auto',
            action='store_true',
            dest='auto',
            default=False,
            help="Automatically search for models with the "
                 "HistoricalRecords field type",
        ),
    )

    # TODO: Add option to set the additional data
    #  from the command line interface
    def handle(self, *args, **options):
        for (model, model_specific_info) in models.registered_models.items():
            additional_data_param_name = model_specific_info[
                'additional_data_param_name']
            excluded_fields_param_name = model_specific_info[
                'excluded_fields_param_name']
            additional_data_field = getattr(model, additional_data_param_name, {})  # noqa
            excluded_fields = getattr(model, excluded_fields_param_name, [])
            self.bulk_history_create(model, additional_data_field,
                                     excluded_fields)

    def bulk_history_create(self, model, additional_data_field={},
                            excluded_fields=[]):
        """Save a copy of all instances to the historical model."""
        if HistoricalRecord.objects.filter(
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.model_name
        ).exists():
            self.stderr.write("{msg} {model}\n".format(
                msg=self.EXISTING_HISTORY_FOUND,
                model=model,
            ))
            return

        sentinel = object()
        historical_instances = []

        for instance in model.objects.all():
            data = {}
            for field in instance._meta.fields:
                if field.attname not in excluded_fields:
                    key = field.attname
                    value = getattr(instance, field.attname, sentinel)
                    if value is not None and value is not sentinel:
                        value = str(value)
                    elif value is sentinel:
                        self.stdout.write(
                            ('Field "{}" is invalid.'.format(key)))
                    data[key] = value
            historical_record = HistoricalRecord(
                history_user=None,
                history_type='+',
                content_object=instance,
                data=data,
                additional_data=dict(
                    (key, str(value)) for (key, value)
                    in additional_data_field.items()
                )
            )
            historical_instances.append(historical_record)
        HistoricalRecord.objects.bulk_create(historical_instances)
