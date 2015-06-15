import threading

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models.query import QuerySet

registered_models = {}


class HistoryLogging(object):
    thread = threading.local()

    def __init__(self, additional_data={}, excluded_fields=[]):
        """
        :param additional_data: This argument is a dict which is used to
        associate any additional data for a model.
        :type additional_data: dict

        :param excluded_fields: This argument is a list which contains the
         names of the fields that are not to be kept a history of.
        :type excluded_fields: list
        """
        self.additional_data = additional_data
        self.excluded_fields = excluded_fields

    def get_history_user(self):
        """Get the modifying user from the middleware."""
        try:
            if self.thread.request.user.is_authenticated():
                return self.thread.request.user
            return None
        except AttributeError:
            return None

    def contribute_to_class(self, cls, name):
        self.manager_name = name
        self.module = cls.__module__
        models.signals.class_prepared.connect(self.finalize, sender=cls)

    def finalize(self, sender, **kwargs):
        if sender not in registered_models:
            registered_models[sender] = {
                'additional_data': self.additional_data,
                'excluded_fields': self.excluded_fields
            }
        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(self.post_save, sender=sender,
                                         weak=False)
        models.signals.post_delete.connect(self.post_delete, sender=sender,
                                           weak=False)
        setattr(sender, self.manager_name, HistoryManager(sender))

    def post_save(self, instance, created, **kwargs):
        if not kwargs.get('raw', False):
            self.create_historical_record(instance, created and '+' or '~')

    def post_delete(self, instance, **kwargs):
        self.create_historical_record(instance, '-')

    def create_historical_record(self, instance, history_type):
        history_user = self.get_history_user()
        sentinel = object()
        history_user_id = history_user.id if history_user else None
        data = {}
        for field in instance._meta.fields:
            if field.attname not in self.excluded_fields:
                key = unicode(field.attname)
                value = getattr(instance, field.attname, sentinel)
                if value is not None and value is not sentinel:
                    value = unicode(value)
                elif value is sentinel:
                    print 'Field "{}" is invalid.'.format(key)
                data[key] = value

        additional_data = dict(
            (unicode(key), unicode(value)) for (key, value)
            in self.additional_data.items()
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
    def __init__(self, type):
        self.type = type

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
        return self.filter(
            content_type__model=model._meta.model_name,
            content_type__app_label=model._meta.app_label
        )


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

    def get_superficial_diff_string(self):
        object_snapshot = self.get_current_snapshot()
        diff_string = '{}d '.format(object_snapshot.get_history_type_display())

        if u'Update' not in diff_string:
            return '{action}{object}'.format(
                action=diff_string,
                object=self.content_type.model.capitalize()
            )

        previous_version = self.get_previous_version_snapshot()

        diff_string += ', '.join([
            '{}'.format(attr.replace('_', ' ').capitalize())
            for (attr, val) in object_snapshot.data.items()
            if (attr, val) not in previous_version.data.items()
        ])
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
