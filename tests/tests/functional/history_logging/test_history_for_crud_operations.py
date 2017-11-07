from __future__ import unicode_literals
from __future__ import print_function

from atris.models import HistoricalRecord, fake_save

from django.utils import six
from django.utils.timezone import now

from pytest import mark

from tests.models import Poll, Choice, Voter


str = unicode if six.PY2 else str  # noqa


@mark.django_db
def test_history_not_recorded_for_untracked_models(voter):
    voter.name = 'abc'
    voter.save()
    voter.delete()
    assert HistoricalRecord.objects.by_model(Voter).exists() is False


@mark.django_db
def test_history_create_for_tracked_models(poll, choice, voter):
    assert choice.id == choice.history.last().object_id
    assert choice.history.last().history_type == '+'
    assert choice.history.last().data['poll'] == str(choice.poll_id)
    assert poll.history.last().object_id == poll.id
    assert poll.history.last().history_type == '+'
    assert poll.history.last().data['question'] == poll.question


@mark.django_db
def test_extra_operation_required_to_log_changes_to_many_to_one_relations_to_untracked_models(  # noqa
        poll, choice, voter):
    # arrange
    assert choice.history.count() == 1
    # act
    fake_save(choice)
    # assert
    assert choice.history.count() == 2
    voter_added = choice.history.first()
    assert voter_added.history_type == '~'
    assert voter_added.history_diff == ['voters']
    assert voter_added.data['voters'] == str(voter.pk)


@mark.django_db
def test_updating_simple_fields_recorded_for_model(poll):
    # arrange
    poll.question = 'updated_question'
    # act
    poll.save()
    # assert
    assert poll.history.count() == 2
    updated_question = poll.history.first()
    assert updated_question.history_type == '~'
    assert updated_question.history_diff == ['question']
    assert updated_question.data['question'] == 'updated_question'


@mark.django_db
def test_updating_related_fields_recorded_for_model(choice, voter):
    # arrange
    new_poll = Poll.objects.create(question='question', pub_date=now())
    choice.poll = new_poll
    another_voter = Voter.objects.create(choice=choice, name='voter_2')
    # act
    choice.save()
    # assert
    assert choice.history.count() == 2
    updated_poll_and_voters = choice.history.first()
    assert updated_poll_and_voters.history_type == '~'
    assert set(updated_poll_and_voters.history_diff) == set(['poll', 'voters'])
    assert updated_poll_and_voters.data['poll'] == str(new_poll.pk)
    expected_voters = '{}, {}'.format(another_voter.pk, voter.pk)
    assert updated_poll_and_voters.data['voters'] == expected_voters


@mark.django_db
def test_history_delete_for_tracked_models(poll):
    # arrange
    poll_id = poll.id
    # act
    poll.delete()
    # assert
    poll_history = HistoricalRecord.objects.by_model_and_model_id(Poll,
                                                                  poll_id)
    assert poll_history.count()
    poll_deleted = poll_history.first()
    assert poll_deleted.history_type == '-'


@mark.django_db
def test_deleting_untracked_instances_requires_fake_save_for_referring_tracked_instance(  # noqa
        choice, voter):
    # arrange
    fake_save(choice)  # Recording the voter on the choice instance
    # act
    voter.delete()
    fake_save(choice)
    # assert
    assert choice.history.count() == 3
    removed_voter = choice.history.first()
    assert removed_voter.history_type == '~'
    assert removed_voter.history_diff == ['voters']
    assert removed_voter.data['voters'] == ''


@mark.django_db
def test_deleting_referenced_tracked_object_tracks_both_delete_operations(
        poll, choice):
    # arrange
    poll_id = poll.pk
    choice_id = choice.pk
    # act
    poll.delete()
    # assert
    poll_history = HistoricalRecord.objects.by_model_and_model_id(Poll,
                                                                  poll_id)
    assert poll_history.count() == 2
    assert poll_history.first().history_type == '-'
    choice_history = HistoricalRecord.objects.by_model_and_model_id(Choice,
                                                                    choice_id)
    assert choice_history.count() == 2
    assert choice_history.first().history_type == '-'


@mark.django_db
def test_history_not_generated_if_no_fields_changed(poll):
    # arrange
    lastest_history = poll.history.first()
    previous_history_count = poll.history.count()
    # act
    poll.save()
    # assert
    assert poll.history.first() == lastest_history
    assert poll.history.count() == previous_history_count
