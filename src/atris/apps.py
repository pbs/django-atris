from django.apps import AppConfig


class AtrisConfig(AppConfig):
    name = 'atris'
    label = 'atris'
    verbose_name = 'Atris Model History'

    def ready(self):
        from atris.models import registered_models
        for sender in registered_models:
            sender._meta.history_logging.register_signal_handlers(sender)
