from __future__ import unicode_literals
from __future__ import print_function

from pytest import mark

from tests.models import Actor, Episode, Link, Show


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
    actor1_episode_updated = actor1.history.filter(
        history_diff__contains=['episode'],
        additional_data__episode='Updated Episode'
    )
    assert actor1_episode_updated.count() == 2
    assert actor1_episode_updated[0].related_field_history == actor2_added
    assert actor1_episode_updated[1].related_field_history == actor1_added
    actor2_episode_updated = actor2.history.filter(
        history_diff__contains=['episode'],
        additional_data__episode='Updated Episode',
        related_field_history=actor2_added
    )
    assert actor2_episode_updated.count() == 1


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
    episode_updates_notifications = season.history.filter(
        related_field_history__isnull=False
    )
    assert episode_updates_notifications.exists() is False
    assert Episode.history.filter(object_id=episode_id).count() == 3


@mark.skip(reason='Issue#16')
@mark.django_db
def test_history_generated_for_previous_interested_object_when_removed_from_observed_object(  # noqa
        show, episode):
    # arrange
    next_show = Show.objects.create(title='Another', description='Another')
    # act
    episode.show = next_show
    episode.save()
    # assert
    show_updated = show.history.first()
    assert show_updated.history_type == '~'
    assert show_updated.history_diff == ['episode']
    assert show_updated.additional_data['episode'] == 'Removed Episode'
    assert show_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_observed_object_removal_will_override_regular_update_message(
        show, episode):
    # arrange
    next_show = Show.objects.create(title='Another', description='Another')
    # act
    episode.show = next_show
    episode.title = 'Another title'
    episode.save()
    # assert
    show_updated = show.history.first()
    assert show_updated.history_type == '~'
    assert show_updated.history_diff == ['episode']
    assert show_updated.additional_data['episode'] == 'Removed Episode'
    assert show_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_history_generated_for_new_interested_object_when_set_on_existing_episode(  # noqa
        show, episode):
    # arrange
    next_show = Show.objects.create(title='Another', description='Another')
    # act
    episode.show = next_show
    episode.save()
    # assert
    next_show_updated = next_show.history.first()
    assert next_show_updated.history_type == '~'
    assert next_show_updated.history_diff == ['episode']
    assert next_show_updated.additional_data['episode'] == 'Added Episode'
    assert next_show_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_moving_observed_object_to_another_interested_object_will_override_regular_update_message(  # noqa
        show, episode):
    # arrange
    next_show = Show.objects.create(title='Another', description='Another')
    # act
    episode.show = next_show
    episode.title = 'Another title'
    episode.save()
    # assert
    next_show_updated = next_show.history.first()
    assert next_show_updated.history_type == '~'
    assert next_show_updated.history_diff == ['episode']
    assert next_show_updated.additional_data['episode'] == 'Added Episode'
    assert next_show_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_history_generated_for_interested_m2m_object_when_observed_object_removed(  # noqa
        show, episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.remove(actor1)
    # assert
    actor1_updated = actor1.history.first()
    assert actor1_updated.history_type == '~'
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Removed Episode'
    assert actor1_updated.related_field_history == episode.history.first()
    actor2_updated = actor2.history.first()
    assert actor2_updated.history_type == '~'
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Updated Episode'
    assert actor2_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_history_generated_for_interested_m2m_object_when_observed_object_added(  # noqa
        show, episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1)
    # act
    episode.cast.add(actor2)
    # assert
    actor1_updated = actor1.history.first()
    assert actor1_updated.history_type == '~'
    assert actor1_updated.history_diff == ['episode']
    assert actor1_updated.additional_data['episode'] == 'Updated Episode'
    assert actor1_updated.related_field_history == episode.history.first()
    actor2_updated = actor2.history.first()
    assert actor2_updated.history_type == '~'
    assert actor2_updated.history_diff == ['episode']
    assert actor2_updated.additional_data['episode'] == 'Added Episode'
    assert actor2_updated.related_field_history == episode.history.first()


@mark.skip(reason='Issue#16')
@mark.django_db
def test_history_generated_for_interested_object_referenced_by_generic_field(
        show):
    # act
    show_url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street',
        related_object=show
    )
    next_show = Show.objects.create(title='Another', description='Another')
    show_url.related_object = next_show
    show_url.save()
    # assert
    show_updated = show.history.first()
    assert show_updated.history_type == '~'
    assert show_updated.history_diff == ['link']
    assert show_updated.additional_data['link'] == 'Removed Link'
    assert show_updated.related_field_history == show_url.history.first()
    next_show_updated = next_show.history.first()
    assert next_show_updated.history_type == '~'
    assert next_show_updated.history_diff == ['link']
    assert next_show_updated.additional_data['link'] == 'Added Link'
    assert next_show_updated.related_field_history == show_url.history.first()


@mark.django_db
def test_modifications_to_interested_object_saved_after_observed_object_is_saved_appear_separately_from_observed_object_notification(  # noqa
        show, episode):
    # act
    show.title = 'Another title'
    episode.title = 'Another title'
    episode.save()
    show.save()
    # assert
    assert show.history.count() == 5
    episode_updated, title_updated = show.history.all()[:2]
    assert episode_updated.history_type == '~'
    assert episode_updated.history_diff == ['episode']
    assert episode_updated.additional_data['episode'] == 'Updated Episode'
    expected_data = {'id': str(show.pk),
                     'title': 'Another title',
                     'description': '',
                     'links': '',
                     'season': '',
                     'specials': str(episode.pk)}
    assert episode_updated.data == expected_data
    assert title_updated.history_type == '~'
    assert title_updated.history_diff == ['title']
    assert title_updated.additional_data == dict()
    assert title_updated.data == expected_data


@mark.django_db
@mark.parametrize('entity', ['show', 'episode'])
def test_modifications_to_interested_generic_fk_saved_after_observed_object_is_saved_appear_separately_from_observed_object_notification(  # noqa
        entity):
    # arrange
    if entity == 'show':
        from tests.tests.functional.history_logging.conftest import show
        obj = show()
        obj_history_count = 5

        def expected_data(url):
            result = {'id': str(obj.pk),
                      'title': 'Another title',
                      'description': '',
                      'links': str(url.pk),
                      'season': '',
                      'specials': ''}
            return result

        def expected_additional_data(**extra_data):
            return dict(**extra_data)

    else:
        from tests.tests.functional.history_logging.conftest import (
            show, writer, episode)
        show = show()
        writer = writer()
        obj = episode(show, writer)
        obj_history_count = 4

        def expected_data(url):
            result = {'id': str(obj.pk),
                      'title': 'Another title',
                      'description': '',
                      'show': str(show.pk),
                      'season': None,
                      'cast': '',
                      'author': str(writer.pk),
                      'co_authors': ''}
            return result

        def expected_additional_data(**extra_data):
            return dict(where_from='System', **extra_data)

    url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street',
        related_object=obj
    )
    # act
    obj.title = 'Another title'
    url.url = 'http://pbs.org/another-title'
    url.save()
    obj.save()
    # assert
    assert obj.history.count() == obj_history_count
    link_updated, title_updated = obj.history.all()[:2]
    assert title_updated.history_type == '~'
    assert title_updated.history_diff == ['title']
    assert title_updated.additional_data == expected_additional_data()
    assert title_updated.data == expected_data(url)
    assert link_updated.history_type == '~'
    assert link_updated.history_diff == ['link']
    assert link_updated.additional_data['link'] == 'Updated Link'
    assert link_updated.data == expected_data(url)
