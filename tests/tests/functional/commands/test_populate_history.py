from io import StringIO

from django.core import management
from django.db import DatabaseError
from pytest import mark

from tests.factories import PollFactory
from tests.models import Poll


@mark.django_db
class TestPopulateCommand:
    def test_initial_populate(self):
        # arrange
        PollFactory.create()

        Poll.history.delete()
        # act
        management.call_command("populate_initial_history")
        # assert
        assert Poll.history.count() == 1

    def test_existing_objects(self):
        # arrange
        out = StringIO()
        PollFactory.create()
        # act
        management.call_command("populate_initial_history", stderr=out)
        # assert
        assert Poll.history.count() == 1
        assert "Existing history found, skipping model" in out.getvalue()

    def test_database_error_logs_message(self, mocker):
        # arrange
        def mock_database_error(*args, **kwargs):
            raise DatabaseError

        mocker.patch(
            "atris.management.commands.populate_initial_history."
            "ModelHistoryCreator.__call__",
            mock_database_error,
        )

        out = StringIO()
        # act
        management.call_command("populate_initial_history", stderr=out)
        # assert
        assert "Error creating history" in out.getvalue()
