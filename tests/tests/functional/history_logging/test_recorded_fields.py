from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import JSONField
from pytest import mark

from atris.models.helpers import get_default_value
from tests.models import Admin, Choice, Episode, Group, Link, Poll, Show, Writer


@mark.django_db
def test_all_wanted_fields_are_present(choice):
    # assert
    choice_created = choice.history.first()
    expected_fields = {"poll", "choice", "votes", "id", "voters"}
    assert set(choice_created.data.keys()) == expected_fields


@mark.django_db
def test_excluded_fields_are_absent(poll, choice):
    # arrange
    poll.question = "Another question"
    poll.save()
    # assert
    # No history generated when a choice is set because the `choices` field is
    # excluded.
    assert poll.history.count() == 2
    modified_question, poll_created = poll.history.all()
    expected_fields = {"question", "pub_date", "custom_id"}
    assert set(modified_question.data.keys()) == expected_fields
    assert set(poll_created.data.keys()) == expected_fields


@mark.django_db
def test_history_not_generated_after_adding_new_model_field_without_changing_its_value(
    poll,
):
    assert poll.history.count() == 1
    # delete question key from the data field of the last history event
    # in order to mimic adding a new field (question) to the poll model, when
    # saving in the future
    last_history_event = poll.history.first()
    del last_history_event.data["question"]
    last_history_event.save()

    assert poll.history.count() == 1
    # if the question field is newly added to the poll model, a history event
    # won't be generated just because there is a new field that was added.
    # history will only be generated when the new field's value changes from
    # its default value to any other value
    poll.question = ""
    poll.save()
    assert poll.history.count() == 1

    poll.question = "modified"
    poll.save()
    assert poll.history.count() == 2
    assert "question" in poll.history.most_recent().history_diff


@mark.parametrize(
    "model, field_name, field_type, expected",
    [
        (Poll, "custom_id", models.AutoField, None),
        (Poll, "question", models.CharField, ""),
        (Poll, "pub_date", models.DateTimeField, None),
        (Poll, "choices", models.ManyToOneRel, ""),
        (Choice, "poll", models.ForeignKey, None),
        (Choice, "votes", models.IntegerField, None),
        (Admin, "groups", models.ManyToManyRel, ""),
        (Group, "admins", models.ManyToManyField, ""),
        (Show, "links", GenericRelation, ""),
        (Episode, "author", models.OneToOneField, None),
        (Writer, "work", models.OneToOneRel, None),
        (Link, "object_id", models.PositiveIntegerField, None),
        (Link, "related_object", GenericForeignKey, None),
        (Episode, "is_published", models.BooleanField, "True"),
        (Episode, "keywords", ArrayField, "[]"),
        (Episode, "episode_metadata", JSONField, "{}"),
    ],
)
def test_get_default_value_helper(model, field_name, field_type, expected):
    # act
    field = model._meta.get_field(field_name)
    # assert
    assert type(field) == field_type
    assert get_default_value(field) == expected
