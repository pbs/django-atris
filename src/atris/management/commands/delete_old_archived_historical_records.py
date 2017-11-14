import logging

from django.core.management import BaseCommand

from atris.models import ArchivedHistoricalRecord

logger = logging.getLogger('old_archived_history_deleting')


class Command(BaseCommand):
    help = """
        Deletes archived historical records older than the specified days or 
        months. You must supply either the days or the weeks param.
    """

    PARAM_ERROR = 'You must supply either the days or the weeks param'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            dest='days',
            type=int,
            default=None,
            help='Any archived historical record older than the number of days '
                 'specified gets deleted.'
        )
        parser.add_argument(
            '--weeks',
            dest='weeks',
            type=int,
            default=None,
            help='Any archived historical record older than the number of '
                 'months specified gets deleted.'
        )

    def handle(self, *args, **options):
        days = options.get('days')
        weeks = options.get('weeks')
        if not (days or weeks):
            self.stderr.write("{msg}\n".format(
                msg=self.PARAM_ERROR,
            ))
            return
        try:
            deleted_entries = ArchivedHistoricalRecord.objects.older_than(
                              days, weeks).delete()
            self.stdout.write('{} archived records deleted.\n'.format(
                deleted_entries[0]))
        except Exception as ex:
            # IndexError from deleted_entries[0] OR other DB issues
            logger.error("Attempt to delete {} failed".format(self.__name__))
