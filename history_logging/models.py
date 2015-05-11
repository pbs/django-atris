import threading
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils import importlib
from django.utils.timezone import now
# from django.contrib.postgres.fields import HStoreField


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

    def finalize(self, sender, **kwargs):
        history_model = self.create_history_model(sender)
        module = importlib.import_module(self.module)
        setattr(module, history_model.__name__, history_model)

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
        data = instance.__dict__
        historical_record = HistoricalRecord.objects.create(
            history_date=history_date,
            history_type=history_type,
            history_user=history_user,
            data=data
        )


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

