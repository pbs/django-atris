from datetime import datetime, timedelta

from django.test import TestCase
from django.core import management

from django.utils.six import StringIO

from tests.models import Poll
from atris.management.commands import (populate_initial_history,
                                       delete_old_historical_records)


class TestPopulateHistory(TestCase):
    command_name = 'populate_initial_history'
    command_error = (management.CommandError, SystemExit)

    def test_initial_populate(self):
        Poll.objects.create(question="Will this populate?",
                            pub_date=datetime.now())
        Poll.history.delete()
        self.assertEqual(0, Poll.history.count())
        management.call_command(self.command_name, auto=True)
        self.assertEqual(1, Poll.history.count())

    def test_existing_objects(self):
        out = StringIO()
        Poll.objects.create(question="Will this populate?",
                            pub_date=datetime.now())
        pre_call_count = Poll.history.count()
        management.call_command(self.command_name, stderr=out)
        self.assertEqual(Poll.history.count(), pre_call_count)
        self.assertIn(populate_initial_history.Command.EXISTING_HISTORY_FOUND,
                      out.getvalue())


class TestDeleteOldHistory(TestCase):
    command_name = 'delete_old_historical_records'

    def test_delete_older_than_days(self):
        out = StringIO()
        poll = Poll.objects.create(question="test", pub_date=datetime.now())
        created_history = poll.history.last()
        created_history.history_date = datetime.now() - timedelta(days=30)
        created_history.save()

        Poll.objects.create(question="test", pub_date=datetime.now())
        pre_delete_count = Poll.history.count()

        # delete all history older than 20 days
        management.call_command(self.command_name, days=20, stdout=out)

        self.assertEquals(pre_delete_count - 1, Poll.history.count())
        self.assertIn('1 deleted.', out.getvalue())

    def test_delete_older_than_weeks(self):
        out = StringIO()
        poll = Poll.objects.create(question="test", pub_date=datetime.now())
        created_history = poll.history.last()
        created_history.history_date = datetime.now() - timedelta(days=8)
        created_history.save()

        Poll.objects.create(question="test", pub_date=datetime.now())
        pre_delete_count = Poll.history.count()

        # delete all history older than 1 week
        management.call_command(self.command_name, weeks=1, stdout=out)

        self.assertEquals(pre_delete_count - 1, Poll.history.count())
        self.assertIn('1 deleted.', out.getvalue())

    def test_no_params_passed_signals_error(self):
        out = StringIO()
        management.call_command(self.command_name, stderr=out)
        self.assertIn(delete_old_historical_records.Command.PARAM_ERROR,
                      out.getvalue())
