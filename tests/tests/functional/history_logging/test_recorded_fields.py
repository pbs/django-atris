from pytest import mark


@mark.django_db
def test_all_wanted_fields_are_present(choice):
    # assert
    choice_created = choice.history.first()
    expected_fields = {'poll', 'choice', 'votes', 'id', 'voters'}
    assert set(choice_created.data.keys()) == expected_fields


@mark.django_db
def test_excluded_fields_are_absent(poll, choice):
    # arrange
    poll.question = 'Another question'
    poll.save()
    # assert
    # No history generated when a choice is set because the `choices` field is
    # excluded.
    assert poll.history.count() == 2
    modified_question, poll_created = poll.history.all()
    expected_fields = {'question', 'pub_date', 'custom_id'}
    assert set(modified_question.data.keys()) == expected_fields
    assert set(poll_created.data.keys()) == expected_fields
