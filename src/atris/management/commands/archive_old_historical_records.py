import logging

from datetime import timedelta

from django.core.management import BaseCommand
from django.db import connection, transaction
from django.utils.timezone import now

from atris.models import get_history_model


logger = logging.getLogger("old_history_archiving")
HistoricalRecord = get_history_model()


class Command(BaseCommand):

    help = """
        Archives historical records older than the specified days or months.
        You must supply either the days or the weeks param.
        The historical entries older than the specified days will be moved to
        the "atris_archivedhistoricalrecord" table.
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
                "the number of days specified gets archived."
            ),
        )
        parser.add_argument(
            "--weeks",
            dest="weeks",
            type=int,
            default=None,
            help=(
                "Any historical record older than "
                "the number of months specified gets archived."
            ),
        )

    def handle(self, *args, **options):
        days = options.get("days")
        weeks = options.get("weeks")
        if not (days or weeks):
            self.stderr.write(f"{self.PARAM_ERROR}\n")
            return
        old_history_entries = HistoricalRecord.objects.older_than(days, weeks)
        handled_entries_nr = old_history_entries.count()
        self.migrate_data(days, weeks)
        self.stdout.write(f"{handled_entries_nr} archived.\n")

    @transaction.atomic
    def migrate_data(self, days=None, weeks=None):
        if days and weeks:
            logger.info(
                "Both days and weeks parameters were supplied for migrating"
                "history records! The weeks parameter will be used as the"
                "delimiter!"
            )
        td = timedelta(weeks=weeks) if weeks else timedelta(days=days)
        older_than_date = now() - td
        cursor = connection.cursor()
        fields_str = ",".join(
            [field.attname for field in HistoricalRecord._meta.fields]
        )
        query = (
            "INSERT INTO atris_archivedhistoricalrecord ({}) "
            "SELECT {} FROM atris_historicalrecord "
            "WHERE history_date < '{}';".format(
                fields_str,
                fields_str,
                older_than_date.date(),
            )
        )
        cursor.execute(query)
        query = (
            "DELETE FROM atris_historicalrecord "
            "WHERE history_date < '{}';".format(
                older_than_date.date(),
            )
        )
        cursor.execute(query)
