import logging

from django.contrib.contenttypes.models import ContentType
from pytest import fail, mark

from atris.models import HistoricalRecord
from tests.factories import ChoiceFactory, PollFactory, VoterFactory
from tests.models import Choice, Episode, Poll, Special


@mark.django_db
def test_get_records_by_app_label_and_model_name_returns_specific_entries():
    # arrange
    PollFactory.create().delete()

    poll = PollFactory.create()
    poll.question = "What's for dinner?"
    poll.save()

    choice = ChoiceFactory.create(poll=poll)

    VoterFactory.create(choice=choice)
    # act
    result = HistoricalRecord.objects.by_app_label_and_model_name(
        Poll._meta.app_label,
        Poll._meta.model_name,
    )
    # assert
    assert result.count() == 4
    poll_content_type = ContentType.objects.get_for_model(Poll)
    by_content_type = result.filter(content_type=poll_content_type)
    assert by_content_type.filter(history_type="+").count() == 2
    assert by_content_type.filter(history_type="-").count() == 1
    assert by_content_type.filter(history_type="~").count() == 1


@mark.django_db
def test_no_records_by_app_label_and_model_name_returned():
    # arrange
    PollFactory.create()
    # act
    result = HistoricalRecord.objects.by_app_label_and_model_name(
        Choice._meta.app_label,
        Choice._meta.model_name,
    )
    # assert
    assert result.exists() is False


@mark.django_db
def test_history_by_model_proxy_and_id_without_proxy_model(episode):
    # assert
    assert episode.history.count() == 1
    assert (
        HistoricalRecord.objects.by_model_proxy_and_id(
            Special,
            episode.id,
        ).count()
        == 1
    )
    assert (
        HistoricalRecord.objects.by_model_and_model_id(
            Special,
            episode.id,
        ).count()
        == 0
    )
    assert (
        HistoricalRecord.objects.by_model_and_model_id(
            Episode,
            episode.id,
        ).count()
        == 1
    )


@mark.django_db
def test_older_than_without_params(poll, caplog):
    # act
    with caplog.at_level(logging.ERROR):
        events = HistoricalRecord.objects.older_than()
    # assert
    assert events is None
    assert "You must supply either the days or the weeks param" in caplog.text


@mark.django_db(transaction=True)
def test_historical_records_approx_count_does_not_raise():
    try:
        HistoricalRecord.objects.approx_count()
    except Exception:
        fail("HistoricalRecord.objects.approx_count() should not raise any error!")
