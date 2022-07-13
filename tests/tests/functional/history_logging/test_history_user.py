from django.contrib.auth.models import User
from pytest import mark


@mark.django_db
def test_no_http_request_and_no_explicit_user_logs_empty_user_in_history(
    poll,
):
    # assert
    poll_created = poll.history.first()
    assert poll_created.history_user is None
    assert poll_created.history_user_id is None


@mark.django_db
def test_user_set_on_instance_recorded_in_history(poll):
    # arrange
    poll.history_user = User(id=1, username="test_user_2")
    poll.question = "Another new question"
    # act
    poll.save()
    # assert
    assert poll.history.count() == 2
    poll_updated = poll.history.first()
    assert poll_updated.history_user == "test_user_2"
    assert poll_updated.history_user_id == 1


@mark.django_db
def test_history_user_id_not_set_when_user_has_no_id(poll):
    # arrange
    poll.history_user = User(username="test_user")
    poll.question = "A new question"
    # act
    poll.save()
    # assert
    poll_updated = poll.history.first()
    assert "test_user" == poll_updated.history_user
    assert poll_updated.history_user_id is None


@mark.django_db
def test_user_full_name_take_precedence_over_username_and_email(poll):
    # arrange
    poll.question = "A new question"
    poll.history_user = User(
        username="test_user",
        first_name="John",
        last_name="Doe",
        email="john.doe@mail.com",
    )
    # act
    poll.save()
    # assert
    assert poll.history.first().history_user == "John Doe"


@mark.django_db
def test_user_email_takes_precedence_over_username(poll):
    # arrange
    poll.question = "A new question"
    poll.history_user = User(username="test_user", email="john.doe@mail.com")
    # act
    poll.save()
    # assert
    assert poll.history.first().history_user == "john.doe@mail.com"


@mark.django_db
def test_users_marked_for_ignore_skip_history(poll):
    # act
    poll.history_user = User(username="ignore_user")
    poll.question = "One user question"
    poll.save()
    poll.history_user = User(id=1010101)
    poll.question = "Another user question"
    poll.save()
    # assert
    assert poll.history.count() == 1  # resulting from create
    assert poll.history.filter(history_user="ignore_user").exists() is False
    assert poll.history.filter(history_user_id=1010101).exists() is False
