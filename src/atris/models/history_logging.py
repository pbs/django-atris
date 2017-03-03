# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import logging
import threading

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils import six

from .historical_record import get_history_model


str = unicode if six.PY2 else str

registered_models = {}

logger = logging.getLogger(__name__)

HistoricalRecord = get_history_model()


# noinspection PyProtectedMember,PyAttributeOutsideInit
class HistoryLogging(object):
    thread = threading.local()

    def __init__(self, additional_data_param_name='',
                 excluded_fields_param_name='',
                 ignore_history_for_users='',
                 interested_related_objects=''):
        """
        :param additional_data_param_name: String used to determine which field
         on the object contains a dict holding any additional data.
        :type additional_data_param_name: str

        :param excluded_fields_param_name: String used to determine which field
            on the object contains a list holding the names of the fields which
            should not be tracked in the history.
        :param ignore_history_for_users: String used to determine which field
            on the object contains a dictionary holding the names of the users
            for which history should not be tracked.
            Dict should contain

        :type excluded_fields_param_name: str
        """
        self.additional_data_param_name = additional_data_param_name
        self.excluded_fields_param_name = excluded_fields_param_name
        self.interested_related_objects_param_name = interested_related_objects
        self.ignore_history_for_users = ignore_history_for_users

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
        # The HistoricalRecord object will be discarded,
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
        history_user, history_user_id = self._get_user_info(instance)
        if self.skip_history_by_user(instance, history_user, history_user_id):
            logger.info("Skipping history instance for user '{}' with user id"
                        " '{}'".format(history_user, history_user_id))
            return

        data = self._get_field_data_from_instance(instance)
        if history_type == '~':
            diff_fields = self._get_diff_fields(data, instance)
        else:
            diff_fields = list()

        additional_data = dict(
            (key, str(value)) for (key, value)
            in getattr(instance, self.additional_data_param_name, {}).items()
        )

        # TODO: Only create History if there are non-excluded fields that differ

        instance_history = HistoricalRecord.objects.create(
            content_object=instance,
            history_type=history_type,
            history_user=history_user,
            history_user_id=history_user_id,
            data=data,
            history_diff=diff_fields,
            additional_data=additional_data
        )

        interested_related_objects = getattr(
            instance, self.interested_related_objects_param_name, [])
        for field_name in interested_related_objects:
            try:
                instance._meta.get_field(field_name)
            except FieldDoesNotExist:
                logger.error('Field "{}" is invalid.'.format(field_name))
            else:
                interested_object = instance.__getattribute__(field_name)
                instance_class_name = instance.__class__.__name__
                instance_name = instance_class_name.lower()
                history_message = '{action}d {object_type}'.format(
                    action=instance_history.get_history_type_display(),
                    object_type=instance_class_name
                )
                HistoricalRecord.objects.create(
                    content_object=interested_object,
                    history_type='~',
                    history_user=history_user,
                    history_user_id=history_user_id,
                    data=self._get_field_data_from_instance(interested_object),
                    history_diff=[instance_name],
                    additional_data={instance_name: history_message},
                    related_field_history=instance_history
                )

    def _get_diff_fields(self, data, instance):
        if instance.history.exists():
            previous_snapshot = instance.history.first()
            return (
                [instance._meta.get_field(attr).verbose_name
                 for (attr, val) in data.items()
                 if (attr, val) not in previous_snapshot.data.items()] or
                ['with no change']
            )
        else:
            return list()

    def skip_history_by_user(self, instance, user, user_id):
        skip_dict = getattr(instance, self.ignore_history_for_users, {})
        ids_with_skip = skip_dict.get('user_ids')
        user_names_to_skip = skip_dict.get('user_names')
        if skip_dict and (
                (user_names_to_skip and (user in user_names_to_skip)) or
                (ids_with_skip and (user_id in ids_with_skip))
        ):
            return True
        return False

    def _get_field_data_from_instance(self, instance):
        data = {}
        excluded_fields = getattr(
            instance, self.excluded_fields_param_name, [])
        for field in instance._meta.fields:
            key = field.attname
            if key not in excluded_fields:
                value = getattr(instance, key)
                data[key] = str(value) if value is not None else str(value)
        return data

    def _get_tracked_fields_from_model(self, model_or_instance):
        pass

    def _get_user_info(self, instance):
        user = self.get_history_user(instance)
        full_name = (user.get_full_name() if callable(
            getattr(user, 'get_full_name', None)) else None)
        username = (user.get_username() if callable(
            getattr(user, 'get_username', None)) else None)
        history_user = (
            full_name or getattr(user, 'email', None) or username
            if user else None
        )
        history_user_id = user.id if user else None
        return history_user, history_user_id


class HistoryManager(object):
    def __get__(self, instance, model):
        if instance and model:
            return HistoricalRecord.objects.by_model_and_model_id(model,
                                                                  instance.id)
        if model:
            return HistoricalRecord.objects.by_model(model)
