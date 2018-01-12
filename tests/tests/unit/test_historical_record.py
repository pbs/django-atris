from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.contrib.contenttypes.models import ContentType

from pytest import fixture

from atris.models import HistoricalRecord

from tests.models import Poll, Choice


@fixture
def poll_content_type():
    return ContentType.objects.get_for_model(Poll)


@fixture
def choice_content_type():
    return ContentType.objects.get_for_model(Choice)


@fixture
def history_setup(poll_content_type, choice_content_type):
    hr1 = HistoricalRecord.objects.create(
        content_type=poll_content_type,
        object_id=3,
        history_type='~',
        data={}
    )
    hr2 = HistoricalRecord.objects.create(
        content_type=choice_content_type,
        object_id=33,
        history_type='-',
        data={}
    )
    hr3 = HistoricalRecord.objects.create(
        content_type=choice_content_type,
        object_id=14,
        history_type='+',
        data={}
    )
    hr4 = HistoricalRecord.objects.create(
        content_type=poll_content_type,
        object_id=3,
        history_type='~',
        data={}
    )
    hr5 = HistoricalRecord.objects.create(
        content_type=poll_content_type,
        object_id=3,
        history_type='-',
        data={}
    )
    hr6 = HistoricalRecord.objects.create(
        content_type=choice_content_type,
        object_id=14,
        history_type='~',
        data={}
    )
    return [hr1, hr2, hr3, hr4, hr5, hr6]


class TestDiffString:

    def test_diff_string_for_create(self, db, poll_content_type):
        # arrange
        create_history = HistoricalRecord.objects.create(
            content_type=poll_content_type,
            object_id=1,
            history_type='+',
            history_diff=[],
            data={'id': '1',
                  'question': 'What?',
                  'pub_date': str(datetime.now())}
        )
        # act
        result = create_history.get_diff_to_prev_string()
        # assert
        assert result == 'Created poll'

    def test_diff_string_for_delete(self, db, poll_content_type):
        # arrange
        create_history = HistoricalRecord.objects.create(
            content_type=poll_content_type,
            object_id=1,
            history_type='-',
            history_diff=[],
            data={'id': '1',
                  'question': 'What?',
                  'pub_date': str(datetime.now())}
        )
        # act
        result = create_history.get_diff_to_prev_string()
        # assert
        assert result == 'Deleted poll'

    def test_diff_string_for_update_with_one_field_updated(self, db,
                                                           poll_content_type):
        # arrange
        update_history = HistoricalRecord.objects.create(
            content_type=poll_content_type,
            object_id=1,
            history_type='~',
            history_diff=['question'],
            data={'id': '1',
                  'question': 'What?',
                  'pub_date': str(datetime.now())}
        )
        # act
        result = update_history.get_diff_to_prev_string()
        # assert
        assert result == 'Updated question'

    def test_diff_string_for_update_with_more_fields_updated(
            self, db, poll_content_type):
        # arrange
        update_history = HistoricalRecord.objects.create(
            content_type=poll_content_type,
            object_id=1,
            history_type='~',
            history_diff=['question', 'pub_date'],
            data={'id': '1',
                  'question': 'What?',
                  'pub_date': str(datetime.now())}
        )
        # act
        result = update_history.get_diff_to_prev_string()
        # assert
        assert result == 'Updated date published, question'

    def test_diff_string_works_properly_with_lost_history(self, db,
                                                          poll_content_type):
        """
        Since old history deletion is a thing, the situation arises that
        history that once had a previous state no longer does and the snapshot
        isn't a "creation" snapshot. In this case, the diff string can't know
        what the difference to the previous state is, so it would return
        'No prior information available.'.

        """
        # arrange
        update_without_previous = HistoricalRecord.objects.create(
            content_type=poll_content_type,
            object_id=1,
            history_type='~',
            history_diff=None,
            data={'id': '1',
                  'question': 'What?',
                  'pub_date': str(datetime.now())}
        )
        # act
        result = update_without_previous.get_diff_to_prev_string()
        # assert
        failure_message = ('Should not have the info required to build the '
                           'history diff.')
        assert result == 'No prior information available.', failure_message


class TestHistoryLoggingOrdering():

    def test_global_history_is_ordered_by_history_date(
            self, db, history_setup):
        expected = list(reversed(history_setup))
        assert list(HistoricalRecord.objects.all()) == expected

    def test_model_history_is_ordered_by_history_date(self, db, history_setup):
        expected_poll_history = [
            history_setup[4], history_setup[3], history_setup[0]
        ]
        assert list(Poll.history.all()) == expected_poll_history
        expected_choice_history = [
            history_setup[5], history_setup[2], history_setup[1]
        ]
        assert list(Choice.history.all()) == expected_choice_history

    def test_model_instance_history_is_ordered_by_history_date(
            self, db, history_setup):
        poll = Poll(custom_id=1, question='Test', pub_date=datetime.now())
        choice = Choice(id=14, poll=poll, choice='a', votes=0)
        expected_choice_history = [history_setup[5], history_setup[2]]
        assert list(choice.history.all()) == expected_choice_history
