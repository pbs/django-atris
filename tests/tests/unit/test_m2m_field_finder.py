from pytest import mark

from atris.models import find_m2m_field_name_by_model
from tests.models import Actor, Episode, Episode2, Group, Special, Writer


@mark.parametrize(
    "instance_model, related_model, reverse_relationship, expected_name, "
    "description",
    [
        (
            Episode,
            Actor,
            False,
            "cast",
            "test name returned for model of related field",
        ),
        (
            Writer,
            Episode,
            True,
            "contributions",
            "test name returned for model of reverse related field",
        ),
        (
            Special,
            Actor,
            False,
            "cast",
            "test name returned for proxy model of inherited related field",
        ),
        (
            Writer,
            Special,
            True,
            "contributions",
            "test name returned for proxy model of reverse related field",
        ),
        (
            Episode2,
            Actor,
            False,
            "cast",
            "test name returned for model of inherited related field",
        ),
        (
            Writer,
            Episode2,
            True,
            "contributions",
            "test name returned for model of inherited reverse related field",
        ),
        (
            Episode2,
            Group,
            False,
            "groups",
            "test name returned for child model of own related field",
        ),
        (
            Group,
            Episode2,
            True,
            "episodes",
            "test name returned for child model of own reverse related field",
        ),
    ],
)
def test_m2m_field_name_returned_for_model(
    instance_model,
    related_model,
    reverse_relationship,
    expected_name,
    description,
):
    assert expected_name == find_m2m_field_name_by_model(
        instance_model._meta,
        related_model,
        reverse_relationship,
    )
