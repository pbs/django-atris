from atris.models import find_m2m_field_name_by_model

from tests.models import Episode, Actor, Writer, Special, Episode2, Group


def test_field_name_returned_for_model_of_related_field():
    # act
    result = find_m2m_field_name_by_model(Episode._meta, Actor, False)
    # assert
    assert result == 'cast'


def test_field_name_returned_for_model_of_reverse_related_field():
    # act
    result = find_m2m_field_name_by_model(Writer._meta, Episode, True)
    # assert
    assert result == 'contributions'


def test_field_name_returned_for_proxy_model_of_inherited_related_field():
    # act
    result = find_m2m_field_name_by_model(Special._meta, Actor, False)
    # assert
    assert result == 'cast'


def test_field_name_returned_for_proxy_model_of_reverse_related_field():
    # act
    result = find_m2m_field_name_by_model(Writer._meta, Special, True)
    # assert
    assert result == 'contributions'


def test_field_name_returned_for_model_of_inherited_related_field():
    # act
    result = find_m2m_field_name_by_model(Episode2._meta, Actor, False)
    # assert
    assert result == 'cast'


def test_field_name_returned_for_model_of_inherited_reverse_related_field():
    # act
    result = find_m2m_field_name_by_model(Writer._meta, Episode2, True)
    # assert
    assert result == 'contributions'


def test_field_name_returned_for_child_model_of_own_related_field():
    # act
    result = find_m2m_field_name_by_model(Episode2._meta, Group, False)
    # assert
    assert result == 'groups'


def test_field_name_returned_for_child_model_of_own_reverse_related_field():
    # act
    result = find_m2m_field_name_by_model(Group._meta, Episode2, True)
    # assert
    assert result == 'episodes'
