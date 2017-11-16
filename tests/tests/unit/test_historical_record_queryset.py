from __future__ import print_function
from __future__ import unicode_literals

from atris.models import HistoricalRecord

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from pytest import mark

from tests.models import Poll, Choice, Voter


@mark.django_db
def test_get_records_by_app_label_and_model_name_returns_specific_entries():
    # arrange
    weather = Poll.objects.create(question='How is the weather?',
                                  pub_date=now())
    dinner = Poll.objects.create(question='What is for dinner',
                                 pub_date=now())
    dinner.question = "What's for dinner?"
    dinner.save()
    weather.delete()
    ham = Choice.objects.create(poll=dinner, choice='Ham & eggs', votes=0)
    Voter.objects.create(choice=ham, name='John')
    # act
    result = HistoricalRecord.objects.by_app_label_and_model_name(
        Poll._meta.app_label, Poll._meta.model_name
    )
    # assert
    assert result.count() == 4
    poll_content_type = ContentType.objects.get_for_model(Poll)
    by_content_type = result.filter(content_type=poll_content_type)
    assert by_content_type.filter(history_type='+').count() == 2
    assert by_content_type.filter(history_type='-').count() == 1
    assert by_content_type.filter(history_type='~').count() == 1


@mark.django_db
def test_no_records_by_app_label_and_model_name_returned():
    # arrange
    Poll.objects.create(question='How is the weather?', pub_date=now())
    # act
    result = HistoricalRecord.objects.by_app_label_and_model_name(
        Choice._meta.app_label, Choice._meta.model_name
    )
    # assert
    assert result.exists() is False
