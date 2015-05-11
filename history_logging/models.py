import threading
import json

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.importlib import import_module
from django.utils.timezone import now
from django.core import serializers


class HistoryLogging(object):
    thread = threading.local()

    def get_history_user(self, instance):
        """Get the modifying user from instance or middleware."""
        try:
            return instance._history_user
        except AttributeError:
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

        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(self.post_save, sender=sender,
                                         weak=False)
        models.signals.post_delete.connect(self.post_delete, sender=sender,
                                           weak=False)

    def post_save(self, instance, created, **kwargs):
        if not created and hasattr(instance, 'skip_history_when_saving'):
            return
        if not kwargs.get('raw', False):
            self.create_historical_record(instance, created and '+' or '~')

    def post_delete(self, instance, **kwargs):
        self.create_historical_record(instance, '-')

    def create_historical_record(self, instance, history_type):
        history_date = getattr(instance, '_history_date', now())
        history_user = self.get_history_user(instance)
        data = serializers.serialize('json', [instance])
        struct = json.loads(data)
        data = dict(
            (key, unicode(val)) for key, val in struct[0]['fields'].items())

        HistoricalRecord.objects.create(
            model_id=instance.id,
            history_object_qualified_path=fullname(instance),
            history_date=history_date,
            history_type=history_type,
            history_user=history_user,
            data=data
        )


def fullname(o):
    """
    Return the full qualified name of a given class.
    :rtype : String
    :param o: Class object.
    """
    return u"{0}.{1}".format(o.__module__, o.__class__.__name__)


class HistoricalRecord(models.Model):
    model_id = models.IntegerField()
    history_object_qualified_path = models.CharField(
        max_length=120, null=False, blank=False
    )
    history_date = models.DateTimeField()
    history_user = models.CharField(max_length=50)
    history_type = models.CharField(max_length=1, choices=(
        ('+', 'Created'),
        ('~', 'Updated'),
        ('-', 'Deleted'),
    ))
    data = HStoreField()

    def __unicode__(self):
        return '{0} {1} id={2}'.format(
            self.get_history_type_display(),
            self.history_object_qualified_path,
            self.model_id
        )

    def get_history_object_class(self):
        """
        Return the class object from the history object dotted path.

        :raises: ValueError if the class could not be loaded
        """
        try:
            module_path, class_name = self.history_object_qualified_path.rsplit(
                ".", 1)
        except ValueError:
            raise ValueError("Invalid class dotted path: %s"
                             % self.history_object_qual_path)

        try:
            module = import_module(module_path)
        except ImportError:
            raise ValueError(
                "Failed to import module: %s" % module_path)

        class_object = getattr(module, class_name, None)
        if class_object is None:
            raise ValueError(
                "No %s class found in module %s" % (class_name, module_path))

        return class_object

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
                and not attr.startswith(('history_', '_'))
            ]
        )
        return diff_string

    def get_current_snapshot(self):
        return self

    def get_previous_version_snapshot(self):
        return HistoricalRecord.objects.filter(
            model_id=self.model_id,
            history_object_qualified_path=self.history_object_qualified_path,
            id__lt=self.id
        ).order_by('-id').first()

    def get_history_object_class_name(self):
        return self.history_object_qual_path.split('.')[-1]

    @classmethod
    def by_model_and_model_id(cls, model, model_id):
        return cls.objects.filter(
            model_id=model_id,
            history_object_qualified_path=fullname(model)
        )

    @classmethod
    def by_model(cls, model):
        print fullname(model)
        return cls.objects.filter(
            history_object_qualified_path=fullname(model)
        )

    def previous_versions(self):
        return HistoricalRecord.objects.filter(
            model_id=self.model_id,
            history_object_qualified_path=self.history_object_qualified_path
        )
