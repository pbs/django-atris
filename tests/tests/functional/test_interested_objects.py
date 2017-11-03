from __future__ import unicode_literals
from __future__ import print_function

from pytest import mark

from tests.models import Show, Season, Actor, Writer, Episode, Link


# TODO: Tests for Issue#11 and Issue#16


@mark.django_db
def test_related_history_created_for_show_and_writer_when_episode_added(
        show, writer):
    # act
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    # assert
    episode_created = episode.history.get(history_type='+')
    show_episode_created = show.history.first()
    assert show_episode_created.related_field_history == episode_created
    assert show_episode_created.history_diff == ['episode']
    assert show_episode_created.additional_data['episode'] == 'Created Episode'
    episode_writer_history = writer.history.first()
    assert episode_writer_history.related_field_history == episode_created
    assert episode_writer_history.history_diff == ['episode']
    assert episode_writer_history.additional_data['episode'] == 'Created Episode'  # noqa


@mark.django_db
def test_related_history_not_created_for_season_when_episode_added():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    season = Season.objects.create(title='Season 2',
                                   description='',
                                   show=show)
    writer = Writer.objects.create(name='David Zabel')
    # act
    Episode.objects.create(
        title='Unknown Soldier',
        description='',
        season=season,
        author=writer
    )
    # assert
    season_episode_history = self._history_for(Season, '~')
    assert season_episode_history.exists()
    episode_history = self._history_for(Episode, '+')
    assert episode_history.exists()


@mark.django_db
def test_related_history_created_for_all_actors_when_cast_added_on_episode():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.add(actor1, actor2)
    # assert
    episode_cast_history = self._history_for(Episode, '~').first()
    actor_updates = self._history_for(Actor, '~')
    actor1_episode_history = actor_updates.get(object_id=actor1.pk)
    assert actor1_episode_history.related_field_history,
                     episode_cast_history)
    assert actor1_episode_history.history_diff, ['episode'])
    assert actor1_episode_history.additional_data['episode'],
                     'Updated Episode')
    actor2_episode_history = actor_updates.get(object_id=actor2.pk)
    assert actor2_episode_history.history_diff, ['episode'])
    assert actor2_episode_history.related_field_history,
                     episode_cast_history)
    assert actor2_episode_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_related_history_created_for_show_writer_when_cast_added_on_episode():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.add(actor1, actor2)
    # assert
    episode_cast_history = self._history_for(Episode, '~').first()
    show_episode_history = self._history_for(Show, '~').first()
    assert show_episode_history.related_field_history,
                     episode_cast_history)
    assert show_episode_history.history_diff, ['episode'])
    assert show_episode_history.additional_data['episode'],
                     'Updated Episode')
    episode_writer_history = self._history_for(Writer, '~').first()
    assert episode_writer_history.related_field_history,
                     episode_cast_history)
    assert episode_writer_history.history_diff, ['episode'])
    assert episode_writer_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_related_history_created_for_all_actors_when_cast_set_on_episode():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    # act
    episode.cast.set([actor1, actor2])
    # assert
    episode_cast_history = self._history_for(Episode, '~').first()
    actor_updates = self._history_for(Actor, '~')
    actor1_episode_history = actor_updates.get(object_id=actor1.pk)
    assert actor1_episode_history.related_field_history,
                     episode_cast_history)
    assert actor1_episode_history.history_diff, ['episode'])
    assert actor1_episode_history.additional_data['episode'],
                     'Updated Episode')
    actor2_episode_history = actor_updates.get(object_id=actor2.pk)
    assert actor2_episode_history.related_field_history,
                     episode_cast_history)
    assert actor2_episode_history.history_diff, ['episode'])
    assert actor2_episode_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_related_history_created_for_actors_when_removing_actor_from_episode_cast():  # noqa
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.remove(actor1)
    # assert
    episode_cast_history = self._history_for(Episode, '~').first()
    actor_updates = self._history_for(Actor, '~')
    actor1_episode_history = actor_updates.filter(
        object_id=actor1.pk,
        related_field_history=episode_cast_history
    ).first()
    assert actor1_episode_history.related_field_history,
                     episode_cast_history)
    assert actor1_episode_history.history_diff, ['episode'])
    assert actor1_episode_history.additional_data['episode'],
                     'Updated Episode')
    actor2_episode_history = actor_updates.filter(
        object_id=actor2.pk
    ).first()
    assert actor2_episode_history.related_field_history,
                     episode_cast_history)
    assert actor2_episode_history.history_diff, ['episode'])
    assert actor2_episode_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_updating_episode_creates_related_history_for_show_writer_actors():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.description = 'Lisette draws the face of a soldier...'
    # assert
    episode_update_history = self._history_for(Episode, '~').first()
    show_episode_history = self._history_for(Show, '~').first()
    assert show_episode_history.related_field_history,
                     episode_update_history)
    assert show_episode_history.additional_data['episode'],
                     'Updated Episode')
    episode_writer_history = self._history_for(Writer, '~').first()
    assert episode_writer_history.related_field_history,
                     episode_update_history)
    assert episode_writer_history.additional_data['episode'],
                     'Updated Episode')
    actor_updates = self._history_for(Actor, '~')
    actor1_episode_history = actor_updates.get(object_id=actor1.pk)
    assert actor1_episode_history.related_field_history,
                     episode_update_history)
    assert actor1_episode_history.additional_data['episode'],
                     'Updated Episode')
    actor2_episode_history = actor_updates.get(object_id=actor2.pk)
    assert actor2_episode_history.related_field_history,
                     episode_update_history)
    assert actor2_episode_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_related_history_created_for_show_writer_when_episode_deleted():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor = Actor.objects.create(name='McKinley Belcher III')
    episode.cast.add(actor)
    # act
    episode.delete()
    # assert
    episode_history = self._history_for(Episode, '-').first()
    show_episode_history = self._history_for(Show, '~').first()
    assert show_episode_history.related_field_history,
                     episode_history)
    assert show_episode_history.history_diff, ['episode'])
    assert show_episode_history.additional_data['episode'],
                     'Deleted Episode')
    episode_writer_history = self._history_for(Writer, '~').first()
    assert episode_writer_history.related_field_history,
                     episode_history)
    assert episode_writer_history.history_diff, ['episode'])
    assert episode_writer_history.additional_data['episode'],
                     'Deleted Episode')


@mark.django_db
def test_related_history_not_created_for_season_when_episode_deleted():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    season = Season.objects.create(title='Season 2',
                                   description='',
                                   show=show)
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     season=season,
                                     author=writer)
    # act
    episode.delete()
    # assert
    season_episode_history = self._history_for(Season, '~')
    assert season_episode_history.exists())
    episode_history = self._history_for(Episode, '-')
    assert episode_history.exists())


@mark.django_db
def test_related_history_created_for_actor_when_episode_deleted():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor = Actor.objects.create(name='McKinley Belcher III')
    episode.cast.add(actor)
    # act
    episode.delete()
    # assert
    episode_history = self._history_for(Episode, '-').first()
    episode_actor_history = self._history_for(Actor, '~').first()
    assert episode_actor_history.related_field_history,
                     episode_history)
    assert episode_actor_history.history_diff, ['episode'])
    assert episode_actor_history.additional_data['episode'],
                     'Deleted Episode')


@mark.django_db
def test_related_history_created_for_actors_when_clearing_episode_cast():
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # act
    episode.cast.clear()
    # assert
    episode_cast_history = self._history_for(Episode, '~').first()
    assert episode_cast_history.history_diff, ['cast'])
    actor_updates = self._history_for(Actor, '~').filter(
        related_field_history=episode_cast_history
    )
    actor1_episode_history = actor_updates.filter(
        object_id=actor1.pk
    ).first()
    assert actor1_episode_history.related_field_history,
                     episode_cast_history)
    assert actor1_episode_history.history_diff, ['episode'])
    assert actor1_episode_history.additional_data['episode'],
                     'Updated Episode')
    actor2_episode_history = actor_updates.filter(
        object_id=actor2.pk
    ).first()
    assert actor2_episode_history.related_field_history,
                     episode_cast_history)
    assert actor2_episode_history.history_diff, ['episode'])
    assert actor2_episode_history.additional_data['episode'],
                     'Updated Episode')


@mark.django_db
def test_related_history_for_interested_generic_foreign_key_with_generic_relation():  # noqa
    # arrange
    show = Show.objects.create(title='Mercy Street', description='')
    # act
    show_url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street',
        related_object=show
    )
    show_url.name = 'PBS'
    show_url.save()
    show_url.delete()
    # assert
    url_on_show_history = self._history_for(Show).filter(
        history_diff__contains=['link'])
    assert url_on_show_history.count(), 3)
    assert url_on_show_history[0].related_field_history,
                     self._history_for(Link, type_='-').first())
    assert url_on_show_history[0].additional_data['link'],
                     'Deleted Link')
    assert url_on_show_history[1].related_field_history,
                     self._history_for(Link, type_='~').first())
    assert url_on_show_history[1].additional_data['link'],
                     'Updated Link')
    assert url_on_show_history[2].related_field_history,
                     self._history_for(Link, type_='+').first())
    assert url_on_show_history[2].additional_data['link'],
                     'Created Link')


@mark.django_db
def test_related_history_for_interested_generic_foreign_key_without_generic_relation():  # noqa
    writer = Writer.objects.create(name='David Zabel')
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     author=writer)
    # act
    episode_url = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street-ep1',
        related_object=episode
    )
    episode_url.url = 'http://pbs.org/mercy-street-unknown-soldier'
    episode_url.save()
    episode_url.delete()
    # assert
    url_on_episode_history = self._history_for(Episode).filter(
        history_diff__contains=['link'])
    assert url_on_episode_history.count(), 3)
    assert url_on_episode_history[0].additional_data['link'],
                     'Deleted Link')
    assert url_on_episode_history[1].additional_data['link'],
                     'Updated Link')
    assert url_on_episode_history[2].additional_data['link'],
                     'Created Link')


def _history_for(class_, type_=None):
    result = HistoricalRecord.objects.filter(
        content_type__app_label=class_._meta.app_label,
        content_type__model=class_._meta.model_name
    )
    if type_ is not None:
        result = result.filter(history_type=type_)
    return result
