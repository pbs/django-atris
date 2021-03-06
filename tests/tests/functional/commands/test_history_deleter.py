from __future__ import unicode_literals
from __future__ import print_function

from datetime import timedelta

from django.core import management
from django.utils.six import StringIO
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType

from pytest import mark

from atris.models import ArchivedHistoricalRecord
from tests.models import Poll


@mark.django_db
def test_delete_older_than_days():
    # arrange
    out = StringIO()
    poll = Poll.objects.create(question="test", pub_date=now())
    created_history = poll.history.last()
    created_history.history_date = now() - timedelta(days=30)
    created_history.save()
    Poll.objects.create(question="test", pub_date=now())
    # act
    management.call_command('delete_old_historical_records',
                            days=20, stdout=out)
    # assert
    assert Poll.history.count() == 1
    assert '1 HistoricalRecord deleted.\n' in out.getvalue()


@mark.django_db
def test_delete_older_than_weeks():
    # arrange
    out = StringIO()
    poll = Poll.objects.create(question="test", pub_date=now())
    created_history = poll.history.last()
    created_history.history_date = now() - timedelta(days=8)
    created_history.save()
    Poll.objects.create(question="test", pub_date=now())
    # act
    management.call_command('delete_old_historical_records',
                            weeks=1, stdout=out)
    # assert
    assert Poll.history.count() == 1
    assert '1 HistoricalRecord deleted.\n' in out.getvalue()


@mark.django_db
def test_no_params_passed_signals_error():
    # arrange
    out = StringIO()
    # act
    management.call_command('delete_old_historical_records', stderr=out)
    # assert
    expected_message = 'You must supply either the days or the weeks param'
    assert expected_message in out.getvalue()


@mark.django_db
def test_delete_archived_older_than_days():
    # arrange
    out = StringIO()
    obj = ArchivedHistoricalRecord.objects.create(
        content_type=ContentType.objects.get_for_model(Poll),
        object_id=13, data={}
    )
    obj.save()  # save with now() history_date since auto_now_add=True
    obj.history_date = now() - timedelta(days=10)
    obj.save()
    # act
    management.call_command('delete_old_historical_records',
                            '--from-archive', days=1, stdout=out)
    # assert
    assert '1 ArchivedHistoricalRecord deleted.\n' in out.getvalue()


@mark.django_db
def test_delete_archived_no_date_error():
    # arrange
    out = StringIO()
    # act
    management.call_command('delete_old_historical_records',
                            '--from-archive', stderr=out)
    # assert
    expected_message = 'You must supply either the days or the weeks param'
    assert expected_message in out.getvalue()
