# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import logging
from sys import modules
import threading

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.utils import six

from .exceptions import InvalidRelatedField
from .helpers import get_diff_fields, get_instance_field_data
from .historical_record import get_history_model


str = unicode if six.PY2 else str  # noqa

registered_models = {}
logger = logging.getLogger(__name__)
HistoricalRecord = get_history_model()


class HistoryManager(object):
    def __get__(self, instance, model):
        if instance and model:
            return HistoricalRecord.objects.by_model_and_model_id(model,
                                                                  instance.id)
        if model:
            return HistoricalRecord.objects.by_model(model)


# noinspection PyProtectedMember,PyAttributeOutsideInit
class HistoryLogging(object):

    thread = threading.local()

    def __init__(self, additional_data_param_name='',
                 excluded_fields_param_name='',
                 ignore_history_for_users='',
                 interested_related_fields=''):
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
        self.interested_related_fields_param_name = interested_related_fields
        self.ignore_history_for_users_param_name = ignore_history_for_users

    def contribute_to_class(self, cls, name):
        if cls not in registered_models:
            registered_models[cls] = {
                'additional_data_param_name': self.additional_data_param_name,
                'excluded_fields_param_name': self.excluded_fields_param_name
            }
        setattr(cls._meta, 'history_logging', self)
        setattr(cls, name, HistoryManager())
        self.module = cls.__module__
        self.model = cls
        self.excluded_fields_names = getattr(
            cls, self.excluded_fields_param_name, [])
        self._set_interested_related_fields(cls)

    def _set_interested_related_fields(self, cls):
        self.interested_related_fields = set()
        interested_related_fields_name = getattr(
            cls, self.interested_related_fields_param_name, [])
        for field_name in interested_related_fields_name:
            field = cls._meta.get_field(field_name)
            if field.is_relation:
                self.interested_related_fields.add(field)
            else:
                raise InvalidRelatedField('{} is not a related field on {}'
                                          .format(field.name, cls))

    def register_signal_handlers(self, sender):
        post_save.connect(self.post_save, sender=sender, weak=False)
        pre_delete.connect(self.pre_delete, sender=sender, weak=False)
        through_classes = get_m2m_through_classes(sender)
        for through_class in through_classes:
            m2m_changed.connect(self.m2m_changed, sender=through_class)

    def post_save(self, instance, created=True, raw=False, **kwargs):
        if not raw:
            self._create_historical_record(instance, created and '+' or '~')

    def pre_delete(self, instance, **kwargs):
        self._create_historical_record(instance, '-')

    def m2m_changed(self, instance, action, reverse, model, pk_set, **kwargs):
        if action == 'post_add':
            self._create_historical_record(instance, '~')
        elif action in ('pre_remove', 'pre_clear'):
            field_name = find_field_name_by_model(
                instance._meta, model, reverse)
            self._create_historical_record(instance, '~', {field_name: pk_set})

    def _create_historical_record(self, instance, history_type,
                                  removed_data=None):
        ignored_users = getattr(
            instance, self.ignore_history_for_users_param_name, {})
        generate_history = HistoricalRecordGenerator(
            instance,
            history_type,
            self.get_history_user_from_request(),
            ignored_users,
            removed_data
        )
        generate_history()

    def get_history_user_from_request(self):
        """Get the modifying user from the middleware."""
        try:
            if self.thread.request.user.is_authenticated():
                return self.thread.request.user
        except AttributeError:
            return


def get_m2m_through_classes(sender):
    m2m_related_throughs = [get_through_class(sender, ro.through)
                            for ro in sender._meta.related_objects
                            if ro.many_to_many]
    m2m_throughs = [get_through_class(sender, f.remote_field.through)
                    for f in sender._meta.local_many_to_many]
    return m2m_related_throughs + m2m_throughs


def get_through_class(model, through):
    if is_str(through):
        module_class = through.rsplit('.', 1)
        class_ = module_class.pop()
        module_path = module_class[0] if module_class else model.__module__
        through = getattr(find_module(module_path), class_)
    return through


def is_str(obj):
    return isinstance(obj, str if six.PY3 else basestring)  # noqa


def find_module(module_path):
    if not module_path.endswith('.models'):
        for path in modules.keys():
            if path.endswith('.models') and module_path in path:
                module_path = path
    return modules[module_path]


def find_field_name_by_model(owning_model_meta, model, on_reverse=None):
    remote_relations = owning_model_meta.related_objects
    local_relations = owning_model_meta.local_many_to_many
    if on_reverse is None:
        fields = list(remote_relations) + list(local_relations)
    elif on_reverse:
        fields = remote_relations
    else:
        fields = local_relations
    for field in fields:
        if field.related_model == model:
            return field.name


class HistoricalRecordGenerator(object):

    def __init__(self, instance, history_type, user, ignored_users=None,
                 removed_data=None):
        self.instance = instance
        self.history_logging = self.instance._meta.history_logging
        self.history_type = history_type
        self.user = user or getattr(instance, 'history_user', None)
        self.ignored_users = ignored_users if ignored_users else {}
        self.history_user, self.history_user_id = self.get_user_info(self.user)
        self.removed_data = removed_data if removed_data else {}

    @staticmethod
    def get_user_info(user):
        if not user:
            return None, None
        full_name = (user.get_full_name() if callable(
            getattr(user, 'get_full_name', None)) else None)
        username = (user.get_username() if callable(
            getattr(user, 'get_username', None)) else None)
        history_user = (
            full_name or getattr(user, 'email', None) or username
            if user else None
        )
        return history_user, user.id

    def __call__(self):
        if self.should_skip_history_for_user():
            logger.info(
                "Skipping history instance for user '{}' with user id "
                "'{}'".format(self.history_user, self.history_user_id)
            )
            return
        data = get_instance_field_data(self.instance, self.removed_data)
        diff_fields, should_generate_history = self.get_differing_fields(data)
        if not should_generate_history:
            return
        self.instance_history = HistoricalRecord.objects.create(
            content_object=self.instance,
            history_type=self.history_type,
            history_user=self.history_user,
            history_user_id=self.history_user_id,
            data=data,
            history_diff=diff_fields,
            additional_data=self.get_additional_data()
        )
        self.generate_history_for_interested_objects()

    def should_skip_history_for_user(self):
        ids_to_skip = self.ignored_users.get('user_ids', [])
        user_names_to_skip = self.ignored_users.get('user_names', [])
        return (self.history_user in user_names_to_skip or
                self.history_user_id in ids_to_skip)

    def get_differing_fields(self, data):
        if self.history_type == '~':
            previous_data = getattr(
                self.instance.history.first(), 'data', None)
            diff_fields = get_diff_fields(
                self.instance, data, previous_data,
                self.history_logging.excluded_fields_names
            )
            should_generate_history = diff_fields is None or diff_fields
        else:
            diff_fields = list()
            should_generate_history = True
        return diff_fields, should_generate_history

    def get_additional_data(self):
        try:
            additional_data = getattr(
                self.instance, self.history_logging.additional_data_param_name)
        except AttributeError:
            result = {}
        else:
            result = {key: str(value)
                      for key, value in additional_data.items()}
        return result

    def generate_history_for_interested_objects(self):
        for field in self.history_logging.interested_related_fields:
            interested_objects = self.get_interested_objects(field)
            for interested_object in interested_objects:
                removed_instance = self.get_data_for_remote_relation_removal(
                    field, interested_object.pk)
                self.generate_history_for_interested_object(interested_object,
                                                            removed_instance)

    def get_data_for_remote_relation_removal(self, field, interested_object):
        is_interested_object_removed_from_instance = (
            field.name in self.removed_data and
            (self.removed_data[field.name] is None or
             interested_object in self.removed_data[field.name])
        )
        if is_interested_object_removed_from_instance:
            remote_field_name = find_field_name_by_model(
                field.related_model._meta, self.instance._meta.model)
            removed_instance = {remote_field_name: [self.instance.pk]}
        else:
            removed_instance = {}
        return removed_instance

    def get_interested_objects(self, field):
        try:
            referenced_object = self.instance.__getattribute__(field.name)
        except ObjectDoesNotExist:
            return []
        if field.one_to_one or field.many_to_one:
            # A single result is guaranteed.
            result = [referenced_object] if referenced_object else []
        elif field.one_to_many or field.many_to_many:
            # The attribute is a RelatedManager instance.
            result = list(referenced_object.all())
        else:
            raise TypeError(
                'Field {} did not match any known related field types. Should '
                'be one of: 1-to-1, 1-to-many, many-to-1, many-to-many.'.
                format(field)
            )
        return result

    def generate_history_for_interested_object(self, interested_object,
                                               removed_data):
        instance_class_name = self.instance.__class__.__name__
        instance_name = instance_class_name.lower()
        history_message = '{action}d {object_type}'.format(
            action=self.instance_history.get_history_type_display(),
            object_type=instance_class_name
        )
        additional_data = self.get_additional_data()
        additional_data[instance_name] = history_message
        HistoricalRecord.objects.create(
            content_object=interested_object,
            history_type='~',
            history_user=self.history_user,
            history_user_id=self.history_user_id,
            data=get_instance_field_data(interested_object, removed_data),
            history_diff=[instance_name],
            additional_data=additional_data,
            related_field_history=self.instance_history
        )
