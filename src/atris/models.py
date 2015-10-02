# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from django.utils import six

str = unicode if six.PY2 else str

import threading

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models.query import QuerySet

registered_models = {}


# noinspection PyProtectedMember,PyAttributeOutsideInit
class HistoryLogging(object):
    thread = threading.local()

    def __init__(self, additional_data_param_name='',
                 excluded_fields_param_name=''):
        """
        :param additional_data_param_name: String used to determine which field
         on the object contains a dict holding any additional data.
        :type additional_data_param_name: str

        :param excluded_fields_param_name: String used to determine which field
            on the object contains a list holding the names of the fields which
            should not be tracked in the history.
        :type excluded_fields_param_name: str
        """
        self.additional_data_param_name = additional_data_param_name
        self.excluded_fields_param_name = excluded_fields_param_name

    def get_history_user(self, instance):
        """Get the modifying user from the middleware."""
        try:
            if self.thread.request.user.is_authenticated():
                return self.thread.request.user
        except AttributeError:
            return getattr(instance, 'history_user', None)

    def contribute_to_class(self, cls, name):
        self.manager_name = name
        self.module = cls.__module__
        models.signals.class_prepared.connect(self.finalize, sender=cls)

    def finalize(self, sender, **kwargs):
        if sender not in registered_models:
            registered_models[sender] = {
                'additional_data_param_name': self.additional_data_param_name,
                'excluded_fields_param_name': self.excluded_fields_param_name
            }
        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(self.post_save, sender=sender,
                                         weak=False)
        models.signals.post_delete.connect(self.post_delete, sender=sender,
                                           weak=False)
        setattr(sender, self.manager_name, HistoryManager())

    def post_save(self, instance, created, **kwargs):
        if not kwargs.get('raw', False):
            self.create_historical_record(instance, created and '+' or '~')

    def post_delete(self, instance, **kwargs):
        self.create_historical_record(instance, '-')

    def create_historical_record(self, instance, history_type):
        user = self.get_history_user(instance)
        full_name = (user.get_full_name() if callable(
            getattr(user, 'get_full_name', None)) else None)
        username = (user.get_username() if callable(
            getattr(user, 'get_username', None)) else None)

        history_user = (
            full_name or getattr(user, 'email', None) or username
            if user else None
        )
        sentinel = object()
        history_user_id = user.id if user else None
        data = {}
        excluded_fields = getattr(instance, self.excluded_fields_param_name, [])
        for field in instance._meta.fields:
            if field.attname not in excluded_fields:
                key = field.attname
                value = getattr(instance, field.attname, sentinel)
                if value is not None and value is not sentinel:
                    value = str(value)
                elif value is sentinel:
                    self.stdout.write(('Field "{}" is invalid.'.format(key)))
                data[key] = value

        additional_data = dict(
            (key, str(value)) for (key, value)
            in getattr(instance, self.additional_data_param_name, {}).items()
        )

        HistoricalRecord.objects.create(
            content_object=instance,
            history_type=history_type,
            history_user=history_user,
            history_user_id=history_user_id,
            data=data,
            additional_data=additional_data
        )


class HistoryManager(object):
    def __get__(self, instance, model):
        if instance and model:
            return HistoricalRecord.objects.by_model_and_model_id(model,
                                                                  instance.id)
        if model:
            return HistoricalRecord.objects.by_model(model)


class HistoricalRecordQuerySet(QuerySet):
    def by_model_and_model_id(self, model, model_id):
        return self.by_model(model).filter(object_id=model_id)

    def by_model(self, model):
        # noinspection PyProtectedMember
        return self.filter(
            content_type__model=model._meta.model_name,
            content_type__app_label=model._meta.app_label
        )

    def most_recent(self):
        return self.first()


class HistoricalRecord(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    history_date = models.DateTimeField(auto_now_add=True)
    history_user = models.CharField(max_length=50, null=True)
    history_user_id = models.PositiveIntegerField(null=True)
    history_type = models.CharField(max_length=1, choices=(
        ('+', 'Create'),
        ('~', 'Update'),
        ('-', 'Delete'),
    ))

    data = HStoreField()
    additional_data = HStoreField(null=True)
    objects = HistoricalRecordQuerySet.as_manager()

    def __unicode__(self):
        return '{history_type} {content_type} id={object_id}'.format(
            history_type=self.get_history_type_display(),
            content_type=self.content_type.model,
            object_id=self.object_id
        )

    class Meta:
        ordering = ['-history_date']

    def get_diff_to_prev_string(self):
        object_snapshot = self.get_current_snapshot()
        diff_string = '{}d '.format(object_snapshot.get_history_type_display())

        if 'Update' not in diff_string:
            return '{action}{object}'.format(
                action=diff_string,
                object=self.content_type.model.capitalize()
            )

        previous_version = self.get_previous_version_snapshot()

        diff_string += ', '.join(sorted([
                                            '{}'.format(attr.replace('_',
                                                                     ' ').capitalize())
                                            for (attr, val) in
                                            object_snapshot.data.items()
                                            if (attr,
                                                val) not in
                                            previous_version.data.items()
                                            ]))

        if diff_string == 'Updated ':
            diff_string += 'with no change'

        return diff_string

    def get_current_snapshot(self):
        return self

    def get_previous_version_snapshot(self):
        return HistoricalRecord.objects.filter(
            object_id=self.object_id,
            content_type=self.content_type,
            id__lt=self.id
        ).order_by('-history_date').first()

    def previous_versions(self):
        return HistoricalRecord.objects.filter(
            object_id=self.object_id,
            content_type=self.content_type
        )
