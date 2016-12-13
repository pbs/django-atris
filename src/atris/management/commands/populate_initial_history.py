# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
# Prevent `/` to return a truncated response. Can be removed in Py3
from __future__ import division  # noqa

from math import ceil
from optparse import make_option

from django.utils import six
from django.core.management import BaseCommand
from django.db import DatabaseError
from django.db.transaction import atomic

from atris.models import HistoricalRecord, registered_models

str = str if six.PY2 else str


class Command(BaseCommand):
    EXISTING_HISTORY_FOUND = 'Existing history found, skipping model'

    SELECT_BATCH_SIZE = 1000
    CREATE_BATCH_SIZE = 1000

    option_list = BaseCommand.option_list + (
        make_option('--select-batch-size',
                    dest='select_batch_size',
                    type='int',
                    default=SELECT_BATCH_SIZE,
                    help='The number of target objects that will be retrieved '
                         'from the DB at one time.'),
        make_option('--create-batch-size',
                    dest='create_batch_size',
                    type='int',
                    default=CREATE_BATCH_SIZE,
                    help='The number of history objects that will be created '
                         'in one batch. Should be at most SELECT_BATCH_SIZE.')
    )

    def handle(self, *args, **options):
        for model, model_specific_info in registered_models.items():
            if HistoricalRecord.objects.by_model(model).exists():
                self.stderr.write('{msg} {model}\n'.format(
                    msg=self.EXISTING_HISTORY_FOUND,
                    model=model,
                ))
                continue
            self.stdout.write('Initializing history for {}\n'.format(model))
            additional_data_param_name = model_specific_info[
                'additional_data_param_name']
            additional_data_field = getattr(model, additional_data_param_name,
                                            {})
            excluded_fields_param_name = model_specific_info[
                'excluded_fields_param_name']
            excluded_fields = getattr(model, excluded_fields_param_name, [])
            create_history_for_model = ModelHistoryCreator(
                model, additional_data_field, excluded_fields,
                options['select_batch_size'], options['create_batch_size'],
                self.stdout
            )
            try:
                with atomic():
                    create_history_for_model()
            except DatabaseError as e:
                self.stderr.write('Error creating history for {}: {}'
                                  .format(model, e))


class ModelHistoryCreator(object):

    def __init__(self, model, additional_data_field, excluded_fields,
                 select_batch_size, create_batch_size, output):
        self.model = model
        self.additional_data_field = additional_data_field
        self.excluded_fields = excluded_fields
        self.select_batch_size = select_batch_size
        self.create_batch_size = create_batch_size
        self.output = output

    def __call__(self):
        objects = self.model.objects
        number_of_batches = int(ceil(objects.count() / self.select_batch_size))
        self.output.write(
            'Processing data in {} batches of {} target objects.\n'
            .format(number_of_batches, self.select_batch_size)
        )
        for multiplicity in range(number_of_batches):
            start = self.select_batch_size * multiplicity
            end = start + self.select_batch_size
            self.create_history_for_objects(objects.all()[start:end])
            self.output.write('Finished batch #{} of {}.\n'
                              .format(multiplicity + 1, number_of_batches))

    def create_history_for_objects(self, objects):
        historical_instances = []
        for instance in objects:
            historical_record = self.create_history_for_object(instance)
            historical_instances.append(historical_record)
        HistoricalRecord.objects.bulk_create(historical_instances,
                                             batch_size=self.create_batch_size)

    def create_history_for_object(self, obj):
        data = self.serialize_object_data(obj)
        additional_data = {
            key: str(value)
            for key, value in self.additional_data_field.items()
        }
        historical_record = HistoricalRecord(
            history_user=None,
            history_type='+',
            content_object=obj,
            data=data,
            additional_data=additional_data
        )
        return historical_record

    def serialize_object_data(self, instance):
        data = {}
        for field in instance._meta.fields:
            if field.attname not in self.excluded_fields:
                key = field.attname
                try:
                    value = getattr(instance, field.attname)
                except AttributeError:
                    self.output.write(('Field "{}" is invalid.'.format(key)))
                else:
                    if value is not None:
                        value = str(value)
                        data[key] = value
        return data
