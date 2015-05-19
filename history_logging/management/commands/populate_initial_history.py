from optparse import make_option

from django.core.management import BaseCommand
from ... import models
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
        for (model, additional_data_field) in models.registered_models.items():
            self.bulk_history_create(model, additional_data_field)

    def bulk_history_create(self, model, additional_data_field):
        """Save a copy of all instances to the historical model."""
        if HistoricalRecord.objects.filter(
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.model_name
        ).exists():
            self.stderr.write("{msg} {model}\n".format(
                msg=self.EXISTING_HISTORY_FOUND,
                model=model,
            ))
        if not additional_data_field:
            additional_data_field = ''
        historical_instances = [
            HistoricalRecord(
                history_user=None,
                history_type='+',
                content_object=instance,
                data=dict((unicode(field.attname),
                           unicode(getattr(instance, field.attname)))
                          for field in instance._meta.fields),
                additional_data=dict(
                    (unicode(key), unicode(value)) for (key, value)
                    in getattr(instance, additional_data_field, {}).items()
                )
            ) for instance in model.objects.all()]
        HistoricalRecord.objects.bulk_create(historical_instances)
