import logging
from optparse import make_option
from atris.models import HistoricalRecord

from django.core.management import BaseCommand

logger = logging.getLogger('old_history_handling')


class Command(BaseCommand):
    help = (
        """
        Handles historical records older than the specified days or months.
        You must supply either the days or the weeks param.
        """
    )

    option_list = BaseCommand.option_list + (
        make_option('--days',
                    dest='days',
                    type='int',
                    default=None,
                    help=('Any historical record older than the number of days'
                          ' specified gets handled.')),
        make_option('--weeks',
                    dest='weeks',
                    type='int',
                    default=None,
                    help=('Any historical record older than the number of'
                          ' months specified gets handled.')),
    )

    def handle(self, *args, **options):
        days = options.get('days')
        weeks = options.get('weeks')
        if not (days or weeks):
            logger.error('You must supply either the days or the weeks param')
            return
        old_history_entries = HistoricalRecord.objects.older_than(days, weeks)
        handled_entries_nr = old_history_entries.count()
        old_history_entries.delete()
        logger.info('{} entries were handled.'.format(handled_entries_nr))
