import logging

from datetime import timedelta
from io import StringIO

from django.core import management
from django.utils.timezone import now
from pytest import mark

from tests.factories import ArchivedHistoricalRecordFactory, PollFactory
from tests.models import Poll


@mark.django_db
class TestDeleteCommand:
    @mark.parametrize(
        "days, delete_command_kwargs",
        [
            (30, {"days": 20}),
            (8, {"weeks": 1}),
        ],
    )
    def test_delete_historical_record(self, days, delete_command_kwargs):
        # arrange
        out = StringIO()
        poll = PollFactory.create()

        created_history = poll.history.last()
        created_history.history_date = now() - timedelta(days=days)
        created_history.save()

        PollFactory.create()
        # act
        management.call_command(
            "delete_old_historical_records",
            stdout=out,
            **delete_command_kwargs,
        )
        # assert
        assert Poll.history.count() == 1
        assert "1 HistoricalRecord deleted." in out.getvalue()

    @mark.parametrize(
        "days, delete_command_kwargs",
        [
            (10, {"days": 3}),
            (15, {"weeks": 2}),
        ],
    )
    def test_delete_archived_historical_record(self, days, delete_command_kwargs):
        # arrange
        out = StringIO()
        event = ArchivedHistoricalRecordFactory.create()
        event.save()  # save with now() history_date since auto_now_add=True
        event.history_date = now() - timedelta(days=days)
        event.save()
        # act
        management.call_command(
            "delete_old_historical_records",
            "--from-archive",
            stdout=out,
            **delete_command_kwargs,
        )
        # assert
        assert "1 ArchivedHistoricalRecord deleted." in out.getvalue()

    def test_call_delete_with_both_days_and_weeks(self, caplog):
        # arrange
        out = StringIO()
        event = ArchivedHistoricalRecordFactory.create()
        event.save()  # save with now() history_date since auto_now_add=True
        event.history_date = now() - timedelta(days=15)
        event.save()
        # act
        with caplog.at_level(logging.INFO):
            management.call_command(
                "delete_old_historical_records",
                "--from-archive",
                stdout=out,
                days=7,
                weeks=3,
            )
        # assert
        assert "0 ArchivedHistoricalRecord deleted." in out.getvalue()
        assert (
            "You supplied both days and weeks, the weeks param "
            "will be used as the delimiter." in caplog.text
        )

    @mark.parametrize(
        "delete_command_args",
        [
            [],  # deletes HistoricalRecords
            ["--from-archive"],  # deletes ArchivedHistoricalRecords
        ],
    )
    def test_delete_no_params_passed_signals_error(self, delete_command_args):
        # arrange
        out = StringIO()
        # act
        management.call_command(
            "delete_old_historical_records",
            *delete_command_args,
            stderr=out,
        )
        # assert
        expected_message = "You must supply either the days or the weeks param"
        assert expected_message in out.getvalue()
