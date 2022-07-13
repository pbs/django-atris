from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .abstract_historical_record import AbstractHistoricalRecord


class HistoricalRecord(AbstractHistoricalRecord):
    pass


def get_history_model():
    try:
        app_label, model = settings.ATRIS_HISTORY_MODEL.lower().split(".")
    except AttributeError:
        return HistoricalRecord
    else:
        content_type = ContentType.objects.get_by_natural_key(app_label, model)
        return content_type.model_class()
