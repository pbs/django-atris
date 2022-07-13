from django.apps import AppConfig


class AtrisConfig(AppConfig):
    name = "atris"
    label = "atris"
    verbose_name = "Atris Model History"

    def ready(self):
        from atris.models import registered_models

        for sender in registered_models:
            # We have access to all the fields of a Django model only after all
            # models have been loaded.
            history_logger = sender._meta.history_logging
            history_logger.set_additional_data_properties(sender)
            history_logger.set_excluded_fields_names(sender)
            history_logger.set_interested_related_fields(sender)
            history_logger.register_signal_handlers(sender)
