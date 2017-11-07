from __future__ import unicode_literals
from __future__ import print_function

from pytest import mark

from tests.models import Actor, Episode, Link


# TODO: Tests for Issue#11 and Issue#16


@mark.django_db
def test_related_history_created_for_interested_objects_when_observed_object_added(  # noqa
        show, writer):
    # act
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    # assert
    episode_created = episode.history.get(history_type='+')
    show_episode_created = show.history.first()
    expected = 'Created Episode'
    assert show_episode_created.related_field_history == episode_created
    assert show_episode_created.history_diff == ['episode']
    assert show_episode_created.additional_data['episode'] == expected
    episode_writer_history = writer.history.first()
    assert episode_writer_history.related_field_history == episode_created
    assert episode_writer_history.history_diff == ['episode']
    assert episode_writer_history.additional_data['episode'] == expected


@mark.django_db
def test_m2m_field_added_to_interested_objects_list_triggers_related_history_for_all_its_items(  # noqa
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.add(actor1)
    episode.cast.add(actor2)
    # assert
    episode_cast_history = episode.history.filter(history_type='~')
    actor2_added = episode_cast_history.first()
    actor1_added = episode_cast_history[1]
    actor1_updates = actor1.history.filter(history_type='~')
    assert actor1_updates.count() == 2
    actor1_history_diff_episode = actor1_updates.filter(
        history_diff__contains=['episode'])
    assert actor1_history_diff_episode.count() == 2
    actor1_additional_data_updated_episode = actor1_updates.filter(
        additional_data__episode='Updated Episode')
    assert actor1_additional_data_updated_episode.count() == 2
    assert actor1_updates[0].related_field_history == actor2_added
    assert actor1_updates[1].related_field_history == actor1_added
    actor2_update = actor2.history.get(history_type='~')
    assert actor2_update.history_diff == ['episode']
    assert actor2_update.related_field_history == actor2_added
    assert actor2_update.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_setting_values_for_an_m2m_field_triggers_related_history_for_all_final_items(  # noqa
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.set([actor1, actor2])
    # assert
    episode_cast_history = episode.history.first()
    actor1_updated = actor1.history.first()
    assert actor1_updated.related_field_history == episode_cast_history
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    actor2_updated = actor2.history.first()
    assert actor2_updated.related_field_history == episode_cast_history
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_setting_values_for_an_m2m_field_triggers_related_history_for_previous_items(  # noqa
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.set([])
    # assert
    episode_cast_history = episode.history.first()
    actor1_updated = actor1.history.first()
    assert actor1_updated.related_field_history == episode_cast_history
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    actor2_updated = actor2.history.first()
    assert actor2_updated.related_field_history == episode_cast_history
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_related_history_created_for_interested_objects_when_m2m_field_updated(
        show, writer, episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.add(actor1, actor2)
    # assert
    episode_cast_history = episode.history.first()
    show_updated = show.history.first()
    assert show_updated.related_field_history == episode_cast_history
    assert show_updated.history_diff == ['episode']
    assert show_updated.additional_data['episode'] == 'Updated Episode'
    writer_updated = writer.history.first()
    assert writer_updated.related_field_history == episode_cast_history
    assert writer_updated.history_diff == ['episode']
    assert writer_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_removing_values_from_an_m2m_field_triggers_related_history_for_all_items(  # noqa
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.remove(actor1)
    # assert
    episode_cast_history = episode.history.first()
    actor1_updated = actor1.history.first()
    assert actor1_updated.related_field_history == episode_cast_history
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    actor2_updated = actor2.history.first()
    assert actor2_updated.related_field_history == episode_cast_history
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_clearing_items_from_m2m_field_triggers_related_history_for_all_items(
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.clear()
    # assert
    episode_cast_history = episode.history.first()
    assert episode_cast_history.history_diff == ['cast']
    actor1_updated = actor1.history.first()
    assert actor1_updated.related_field_history == episode_cast_history
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    actor2_updated = actor2.history.first()
    assert actor2_updated.related_field_history == episode_cast_history
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_updating_attributes_for_observed_object_triggers_related_history_for_all_interested_objects(  # noqa
        show, writer, episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.description = 'Lisette draws the face of a soldier...'
    # assert
    episode_update_history = episode.history.first()
    show_updated = show.history.first()
    assert show_updated.related_field_history == episode_update_history
    assert show_updated.additional_data['episode'] == 'Updated Episode'
    writer_updated = writer.history.first()
    assert writer_updated.related_field_history == episode_update_history
    assert writer_updated.additional_data['episode'] == 'Updated Episode'
    actor1_updated = actor1.history.first()
    assert actor1_updated.related_field_history == episode_update_history
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    actor2_updated = actor2.history.first()
    assert actor2_updated.related_field_history == episode_update_history
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'


@mark.django_db
def test_deleting_observed_object_triggers_related_history_for_all_interested_objects(  # noqa
        show, writer, episode):
    # arrange
    actor = Actor.objects.create(name='McKinley Belcher III')
    episode.cast.add(actor)
    episode_id = episode.pk
    # act
    episode.delete()
    # assert
    episode_deleted = Episode.history.filter(object_id=episode_id).first()
    show_updated = show.history.first()
    assert show_updated.related_field_history == episode_deleted
    assert show_updated.history_diff == ['episode']
    assert show_updated.additional_data['episode'] == 'Deleted Episode'
    writer_updated = writer.history.first()
    assert writer_updated.related_field_history == episode_deleted
    assert writer_updated.history_diff == ['episode']
    assert writer_updated.additional_data['episode'] == 'Deleted Episode'
    actor_updated = actor.history.first()
    assert actor_updated.related_field_history == episode_deleted
    assert actor_updated.history_diff == ['episode']
    assert actor_updated.additional_data['episode'] == 'Deleted Episode'


@mark.django_db
def test_related_history_for_interested_generic_foreign_key_with_generic_relation(  # noqa
        show):
    # act
    show_url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street',
        related_object=show
    )
    show_url.name = 'PBS'
    show_url.save()
    show_url_id = show_url.pk
    show_url.delete()
    # assert
    show_updates = show.history.filter(history_diff__contains=['link'])
    assert show_updates.count() == 3
    url_deleted, url_updated, url_created = Link.history.filter(
        object_id=show_url_id)
    assert show_updates[0].related_field_history == url_deleted
    assert show_updates[0].additional_data['link'] == 'Deleted Link'
    assert show_updates[1].related_field_history == url_updated
    assert show_updates[1].additional_data['link'] == 'Updated Link'
    assert show_updates[2].related_field_history == url_created
    assert show_updates[2].additional_data['link'] == 'Created Link'


@mark.django_db
def test_related_history_for_interested_generic_foreign_key_without_generic_relation(  # noqa
        episode):
    # act
    episode_url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street-ep1',
        related_object=episode
    )
    episode_url.url = 'http://pbs.org/mercy-street-unknown-soldier'
    episode_url.save()
    episode_url_id = episode_url.pk
    episode_url.delete()
    # assert
    episode_updates = episode.history.filter(history_diff__contains=['link'])
    assert episode_updates.count() == 3
    url_deleted, url_updated, url_created = Link.history.filter(
        object_id=episode_url_id)
    assert episode_updates[0].related_field_history == url_deleted
    assert episode_updates[0].additional_data['link'] == 'Deleted Link'
    assert episode_updates[1].related_field_history == url_updated
    assert episode_updates[1].additional_data['link'] == 'Updated Link'
    assert episode_updates[2].related_field_history == url_created
    assert episode_updates[2].additional_data['link'] == 'Created Link'


@mark.django_db
def test_related_history_not_created_for_objects_not_added_in_interested_fields(  # noqa
        show, writer, season):
    # act
    episode = Episode.objects.create(
        title='Unknown Soldier',
        description='',
        season=season,
        author=writer
    )
    episode_id = episode.pk
    episode.title = 'Another title'
    episode.save()
    episode.delete()
    # assert
    assert season.history.count() == 1
    assert Episode.history.filter(object_id=episode_id).count() == 3
