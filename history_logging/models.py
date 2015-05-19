import threading

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import HStoreField
from django.db import models

registered_models = []


class HistoryLogging(object):
    thread = threading.local()

    def __init__(self, additional_data=None):
        """
        :param additional_data: str : This field specifies which field in the
        model refers to additional data. Done this way in order to avoid any
        conflicts with any possible already existing fields and allow for
        greater flexibility. If left with the default value of None, the library
        doesn't check for any additional data.
        """
        self.additional_data = additional_data

    def get_history_user(self):
        """Get the modifying user from the middleware."""
        return self.thread.request.user

    def contribute_to_class(self, cls, name):
        self.manager_name = name
        self.module = cls.__module__
        models.signals.class_prepared.connect(self.finalize, sender=cls)

    def finalize(self, sender, **kwargs):
        if sender not in registered_models:
            registered_models.append(sender)
        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(self.post_save, sender=sender,
                                         weak=False)
        models.signals.post_delete.connect(self.post_delete, sender=sender,
                                           weak=False)

    def post_save(self, instance, created, **kwargs):
        if not kwargs.get('raw', False):
            self.create_historical_record(instance, created and '+' or '~')

    def post_delete(self, instance, **kwargs):
        self.create_historical_record(instance, '-')

    def create_historical_record(self, instance, history_type):
        history_user = self.get_history_user(instance)
        data = dict((unicode(field.attname),
                     unicode(getattr(instance, field.attname)))
                    for field in instance._meta.fields)

        additional_data = dict(
            (unicode(key), unicode(value)) for (key, value)
            in getattr(instance, self.additional_data)
        )

        HistoricalRecord.objects.create(
            content_object=instance,
            history_type=history_type,
            history_user=history_user,
            history_user=history_user.id,
            data=data,
            additional_data=additional_data
        )


class HistoricalRecord(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    history_date = models.DateTimeField(auto_now_add=True)
    history_user = models.CharField(max_length=50, null=True)
    history_user_id = models.PositiveIntegerField()
    history_type = models.CharField(max_length=1, choices=(
        ('+', 'Created'),
        ('~', 'Updated'),
        ('-', 'Deleted'),
    ))

    data = HStoreField()
    additional_data = HStoreField(null=True)

    def __unicode__(self):
        return '{0} {1} id={2}'.format(
            self.get_history_type_display(),
            self.content_type.model,
            self.object_id
        )

    def get_superficial_diff_string(self):
        object_snapshot = self.get_current_snapshot()
        diff_string = u'{} '.format(object_snapshot.get_history_type_display())

        if u'Updated' not in diff_string:
            return diff_string

        previous_version = self.get_previous_version_snapshot()

        diff_string += ', '.join(
            [
                '{}'.format(attr.replace('_', ' ').capitalize())
                for (attr, val) in object_snapshot.data.items()
                if (attr, val) not in previous_version.data.items()
            ]
        )
        return diff_string

    def get_current_snapshot(self):
        return self

    def get_previous_version_snapshot(self):
        return HistoricalRecord.objects.filter(
            object_id=self.object_id,
            content_type=self.content_type
        ).order_by('-history_date').first()

    @classmethod
    def by_model_and_model_id(cls, model, model_id):
        return cls.objects.filter(
            object_id=model_id,
            content_type__model=model._meta.model_name,
            content_type__app_label=model._meta.app_label
        )

    @classmethod
    def by_model(cls, model):
        return cls.objects.filter(
            content_type__model=model._meta.model_name,
            content_type__app_label=model._meta.app_label
        )

    def previous_versions(self):
        return HistoricalRecord.objects.filter(
            object_id=self.object_id,
            content_type=self.content_type
        )