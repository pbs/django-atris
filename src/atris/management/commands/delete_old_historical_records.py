import logging

from django.core.management import BaseCommand

from atris.models import ArchivedHistoricalRecord, get_history_model


logger = logging.getLogger("old_history_deleting")
HistoricalRecord = get_history_model()


class Command(BaseCommand):
    help = """
        Deletes historical records older than the specified days or months.
        You must supply either the days or the weeks param.
    """

    PARAM_ERROR = "You must supply either the days or the weeks param"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            dest="days",
            type=int,
            default=None,
            help=(
                "Any historical record older than "
                "the number of days specified gets deleted."
            ),
        )
        parser.add_argument(
            "--weeks",
            dest="weeks",
            type=int,
            default=None,
            help=(
                "Any historical record older than "
                "the number of months specified gets deleted."
            ),
        )
        parser.add_argument(
            "--from-archive",
            dest="from_archive",
            default=False,
            action="store_true",
            help=(
                'Delete occurs on the "archived historical records" table '
                'instead of the default "historical records" table.'
            ),
        )

    def handle(self, *args, **options):
        days = options.get("days")
        weeks = options.get("weeks")
        if not (days or weeks):
            self.stderr.write(f"{self.PARAM_ERROR}\n")
            return

        model = (
            ArchivedHistoricalRecord
            if options.get("from_archive")
            else HistoricalRecord
        )
        deleted_entries = model.objects.older_than(days, weeks).delete()
        self.stdout.write(f"{deleted_entries[0]} {model.__name__} deleted.\n")
