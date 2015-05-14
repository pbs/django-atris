from optparse import make_option

from django.core.management import BaseCommand
from ... import models
from django.utils.timezone import now
from history_logging.models import HistoricalRecord


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

    def handle(self, *args, **options):
        for model in models.registered_models:
            self.bulk_history_create(model)

    def bulk_history_create(self, model):
        """Save a copy of all instances to the historical model."""
        if HistoricalRecord.objects.filter(
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.model_name
        ).exists():
            self.stderr.write("{msg} {model}\n".format(
                msg=self.EXISTING_HISTORY_FOUND,
                model=model,
            ))
        historical_instances = [
            HistoricalRecord(
                history_date=now(),
                history_user=None,
                history_type='+',
                content_object=instance,
                data=dict((unicode(field.attname),
                           unicode(getattr(instance, field.attname)))
                          for field in instance._meta.fields)
            ) for instance in model.objects.all()]
        HistoricalRecord.objects.bulk_create(historical_instances)