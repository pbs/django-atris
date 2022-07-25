import logging

from datetime import timedelta
from io import StringIO

from django.core import management
from django.utils.timezone import now
from pytest import mark

from atris.models import ArchivedHistoricalRecord
from tests.factories import PollFactory
from tests.models import Poll


@mark.django_db
class TestArchiveCommand:
    @mark.parametrize(
        "days, archive_kwargs",
        [
            (30, {"days": 20}),
            (8, {"weeks": 1}),
        ],
    )
    def test_archive_history_event(self, days, archive_kwargs):
        # arrange
        out = StringIO()
        poll = PollFactory.create()

        created_history = poll.history.last()
        created_history.history_date = now() - timedelta(days=days)
        created_history.save()

        PollFactory.create()
        # act
        management.call_command(
            "archive_old_historical_records",
            stdout=out,
            **archive_kwargs,
        )
        # assert
        assert Poll.history.count() == 1
        assert "1 archived." in out.getvalue()
        assert ArchivedHistoricalRecord.objects.count() == 1

    def test_archive_history_event_with_both_weeks_and_days_params(self, caplog):
        # if both days and weeks params are supplied to the command,
        # the weeks param will be used and a message will be logged
        out = StringIO()
        poll = PollFactory.create()

        created_history = poll.history.last()
        created_history.history_date = now() - timedelta(days=20)
        created_history.save()

        PollFactory.create()
        # act
        with caplog.at_level(logging.INFO):
            management.call_command(
                "archive_old_historical_records",
                days=10,
                weeks=3,
                stdout=out,
            )
        # assert
        assert Poll.history.count() == 2
        assert "0 archived." in out.getvalue()
        assert "Both days and weeks parameters were supplied" in caplog.text
        assert ArchivedHistoricalRecord.objects.count() == 0

    def test_no_params_passed_signals_error(self):
        # arrange
        out = StringIO()
        # act
        management.call_command("archive_old_historical_records", stderr=out)
        # assert
        expected_message = "You must supply either the days or the weeks param"
        assert expected_message in out.getvalue()
