# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from datetime import timedelta
import logging
import threading

from django.utils import six
from django.utils.timezone import now
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models
from django.db.models.query import QuerySet

str = unicode if six.PY2 else str

registered_models = {}

logger = logging.getLogger(__name__)


# noinspection PyProtectedMember,PyAttributeOutsideInit
class HistoryLogging(object):
    thread = threading.local()

    def __init__(self, additional_data_param_name='',
                 excluded_fields_param_name='',
                 ignore_history_for_users=''):
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
        history_user, history_user_id = self._get_user_info(instance)
        if self.skip_history_by_user(instance, history_user, history_user_id):
            logger.info("Skipping history instance for user '{}' with user id"
                        " '{}'".format(history_user, history_user_id))
            return

        data = self._get_fields_from_instance(instance)
        diff_fields = self._get_diff_fields(data, instance)

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
            history_diff=diff_fields,
            additional_data=additional_data
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
            return []

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

    def _get_fields_from_instance(self, instance):
        sentinel = object()
        data = {}
        excluded_fields = getattr(instance, self.excluded_fields_param_name, [])
        for field in instance._meta.fields:
            if field.attname not in excluded_fields:
                key = field.attname
                value = getattr(instance, field.attname, sentinel)
                if value is not None and value is not sentinel:
                    value = str(value)
                elif value is sentinel:
                    logger.error(('Field "{}" is invalid.'.format(key)))
                data[key] = value
        return data

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


class HistoricalRecordQuerySet(QuerySet):
    def by_model_and_model_id(self, model, model_id):
        """
        Gets historical records by model and model id, so, basically the
        historical records for an instance of a model.
        :param model: Model which has the HistoricalRecord field.
        :param model_id: The model id for which you wish to get the history.
        :return: The instance's history.
        :rtype HistoricalRecord
        """
        return self.by_model(model).filter(object_id=model_id)

    def by_model(self, model):
        # noinspection PyProtectedMember
        """
        Gets historical records by model.
        :param model: Model which has the HistoricalRecord field.
        :return: The entire model's history.
        :rtype HistoricalRecord
        """
        return self.filter(
            content_type__model=model._meta.model_name,
            content_type__app_label=model._meta.app_label
        )

    def most_recent(self):
        """
        Gets the most recent historical record added to the database.
        :return: The most recent historical record added to the database.
        :rtype HistoricalRecord
        """
        return self.first()

    def older_than(self, days=None, weeks=None):
        """
        Gets all historical record entries that are older than either the
        number of days or the number of weeks passed.
        The weeks parameter will be preferred if both are supplied.
        :param days: Number of days old a historical record can be, at most.
        :param weeks: Number of weeks old a historical record can be, at most.
        :return: All the historical record entries that are older than the
                 given param.
        :rtype list(HistoricalRecord)
        """
        if not (days or weeks):
            logger.error('You must supply either the days or the weeks param')
            return
        elif days and weeks:
            logger.info('You supplied both days and weeks, weeks param'
                        ' will be used as the delimiter.')
        td = timedelta(weeks=weeks) if weeks else timedelta(days=days)
        return self.filter(history_date__lte=now() - td)

    def previous_version_by_model_and_id(self, model, object_id, history_id):
        """
        Returns the second to last snapshot of the history for model and
        instance id that is given.
        :param history_id: Id for history snapshot.
        :param model: The model for which the snapshot is for.
        :param object_id: The model ID for which the snapshot is for.
        :return: The previous to HistoricalRecord

        """
        main_qs = self.filter(
            content_type__model=model.model,
            content_type__app_label=model.app_label,
            object_id=object_id,
            id__lt=history_id
        )
        if main_qs.count() <= 0:
            return None
        result = main_qs.order_by('-history_date').first()

        return result


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

    history_diff = ArrayField(models.CharField(max_length=200),
                              blank=True, null=True)

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
        """
        Generates a string which describes the changes that occurred between
        this historical record instance (self) and its previous version.

        :return: Said string.
        :rtype String
        """
        diff_string = '{}d '.format(self.get_history_type_display())

        if 'Update' not in diff_string:
            return '{action}{object}'.format(
                action=diff_string,
                object=self.content_type.model.capitalize()
            )

        if self.history_diff is None:
            previous_version = self._get_prev_version()
            if previous_version:
                self.history_diff = (
                    [self.content_type.model_class()._meta.get_field(
                        attr).verbose_name for
                     (attr, val) in self.data.items()
                     if (attr, val) not in previous_version.data.items()] or
                    ['with no change']
                )
            else:
                self.history_diff = []
            self.save()

        if not self.history_diff:
            return 'No prior information available.'

        diff_string += ', '.join(sorted(self.history_diff))

        return diff_string

    def _get_prev_version(self):
        return HistoricalRecord.objects.previous_version_by_model_and_id(
            model=self.content_type,
            object_id=self.object_id,
            history_id=self.id
        )
