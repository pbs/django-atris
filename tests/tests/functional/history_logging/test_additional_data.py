from pytest import mark

from tests.models import Poll


@mark.django_db
def test_additional_data_default_taken_from_model(poll):
    # assert
    poll_created = poll.history.first()
    assert poll_created.additional_data == {'where_from': 'Import'}


@mark.django_db
def test_default_additional_data_not_set_if_not_defined_on_model(choice):
    # assert
    choice_created = choice.history.first()
    assert choice_created.additional_data == dict()


@mark.django_db
def test_additional_data_set_to_value_from_instance(poll):
    # arrange
    poll.question = 'Modified question'
    poll.additional_data['where_from'] = 'API'
    poll.additional_data['something_particular'] = 'Something'
    # act
    poll.save()
    # assert
    poll_updated = poll.history.first()
    expected = {'where_from': 'API', 'something_particular': 'Something'}
    assert poll_updated.additional_data == expected
    # TODO: Remove after fixing Issue#14
    Poll.additional_data = {'where_from': 'Import'}


@mark.skip(reason='Issue#14: default additional_data not immutable')
@mark.django_db
def test_default_additional_data_not_modified_when_changing_it_on_the_instance(
        poll):
    # act
    poll.additional_data['where_from'] = 'API'
    poll.additional_data['something_particular'] = 'This is specific'
    # assert
    assert Poll.additional_data == {'where_from': 'Import'}


@mark.skip(reason='Will work when solving Issue#14')
@mark.django_db
def test_additiona_data_without_default_can_be_set_on_the_instance(choice):
    # arrange
    choice.votes = 1
    choice.additional_data['where_from'] = 'System'
    # act
    choice.save()
    # assert
    assert choice.history.count() == 2
    updated_votes = choice.history.first()
    assert updated_votes.additional_data == {'where_from': 'System'}


@mark.django_db
def test_explicitly_set_additional_data_on_instance_without_default(choice):
    # arrange
    choice.additional_data = {'where_from': 'System'}
    choice.votes = 1
    # act
    choice.save()
    # assert
    assert choice.history.count() == 2
    assert choice.history.first().additional_data['where_from'] == 'System'


@mark.django_db
def test_history_with_additional_data_not_recorded_if_nothing_changed_on_instance(  # noqa
        poll):
    # arrange
    poll.additional_data['where_from'] = 'API'
    # act
    poll.save()
    # assert
    assert poll.history.filter(history_type='~').exists() is False
