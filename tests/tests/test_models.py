# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from unittest import TestCase
from django.utils import six

from django.contrib.contenttypes.models import ContentType

from django.utils.timezone import now

from atris.models import HistoricalRecord
from tests.models import (
    Poll, Choice, Voter, Show, Season, Actor, Writer, Episode, Link
)


str = unicode if six.PY2 else str


class TestRelatedHistory(TestCase):

    def setUp(self):
        HistoricalRecord.objects.all().delete()

    def test_related_history_created_for_show_and_writer_when_episode_added(
            self):
        # arrange
        show = Show.objects.create(title='Mercy Street', description='')
        writer = Writer.objects.create(name='David Zabel')
        # act
        Episode.objects.create(title='Unknown Soldier',
                               description='',
                               show=show,
                               author=writer)
        # assert
        episode_history = self._history_for(Episode, '+').first()
        show_episode_history = self._history_for(Show, '~').first()
        self.assertEqual(show_episode_history.related_field_history,
                         episode_history)
        self.assertEqual(show_episode_history.history_diff, ['episode'])
        self.assertEqual(show_episode_history.additional_data['episode'],
                         'Created Episode')
        episode_writer_history = self._history_for(Writer, '~').first()
        self.assertEqual(episode_writer_history.related_field_history,
                         episode_history)
        self.assertEqual(episode_writer_history.history_diff, ['episode'])
        self.assertEqual(episode_writer_history.additional_data['episode'],
                         'Created Episode')

    def test_related_history_not_created_for_season_when_episode_added(self):
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
        self.assertFalse(season_episode_history.exists())
        episode_history = self._history_for(Episode, '+')
        self.assertTrue(episode_history.exists())

    def test_related_history_created_for_all_actors_when_cast_added_on_episode(
            self):
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
        self.assertEqual(actor1_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor1_episode_history.history_diff, ['episode'])
        self.assertEqual(actor1_episode_history.additional_data['episode'],
                         'Updated Episode')
        actor2_episode_history = actor_updates.get(object_id=actor2.pk)
        self.assertEqual(actor2_episode_history.history_diff, ['episode'])
        self.assertEqual(actor2_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor2_episode_history.additional_data['episode'],
                         'Updated Episode')

    def test_related_history_created_for_show_writer_when_cast_added_on_episode(  # noqa
            self):
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
        self.assertEqual(show_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(show_episode_history.history_diff, ['episode'])
        self.assertEqual(show_episode_history.additional_data['episode'],
                         'Updated Episode')
        episode_writer_history = self._history_for(Writer, '~').first()
        self.assertEqual(episode_writer_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(episode_writer_history.history_diff, ['episode'])
        self.assertEqual(episode_writer_history.additional_data['episode'],
                         'Updated Episode')

    def test_related_history_created_for_all_actors_when_cast_set_on_episode(
            self):
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
        self.assertEqual(actor1_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor1_episode_history.history_diff, ['episode'])
        self.assertEqual(actor1_episode_history.additional_data['episode'],
                         'Updated Episode')
        actor2_episode_history = actor_updates.get(object_id=actor2.pk)
        self.assertEqual(actor2_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor2_episode_history.history_diff, ['episode'])
        self.assertEqual(actor2_episode_history.additional_data['episode'],
                         'Updated Episode')

    def test_related_history_created_for_actors_when_removing_actor_from_episode_cast(  # noqa
            self):
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
        self.assertEqual(actor1_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor1_episode_history.history_diff, ['episode'])
        self.assertEqual(actor1_episode_history.additional_data['episode'],
                         'Updated Episode')
        actor2_episode_history = actor_updates.filter(
            object_id=actor2.pk
        ).first()
        self.assertEqual(actor2_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor2_episode_history.history_diff, ['episode'])
        self.assertEqual(actor2_episode_history.additional_data['episode'],
                         'Updated Episode')

    def test_updating_episode_creates_related_history_for_show_writer_actors(
            self):
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
        self.assertEqual(show_episode_history.related_field_history,
                         episode_update_history)
        self.assertEqual(show_episode_history.additional_data['episode'],
                         'Updated Episode')
        episode_writer_history = self._history_for(Writer, '~').first()
        self.assertEqual(episode_writer_history.related_field_history,
                         episode_update_history)
        self.assertEqual(episode_writer_history.additional_data['episode'],
                         'Updated Episode')
        actor_updates = self._history_for(Actor, '~')
        actor1_episode_history = actor_updates.get(object_id=actor1.pk)
        self.assertEqual(actor1_episode_history.related_field_history,
                         episode_update_history)
        self.assertEqual(actor1_episode_history.additional_data['episode'],
                         'Updated Episode')
        actor2_episode_history = actor_updates.get(object_id=actor2.pk)
        self.assertEqual(actor2_episode_history.related_field_history,
                         episode_update_history)
        self.assertEqual(actor2_episode_history.additional_data['episode'],
                         'Updated Episode')

    def test_related_history_created_for_show_writer_when_episode_deleted(
            self):
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
        self.assertEqual(show_episode_history.related_field_history,
                         episode_history)
        self.assertEqual(show_episode_history.history_diff, ['episode'])
        self.assertEqual(show_episode_history.additional_data['episode'],
                         'Deleted Episode')
        episode_writer_history = self._history_for(Writer, '~').first()
        self.assertEqual(episode_writer_history.related_field_history,
                         episode_history)
        self.assertEqual(episode_writer_history.history_diff, ['episode'])
        self.assertEqual(episode_writer_history.additional_data['episode'],
                         'Deleted Episode')

    def test_related_history_not_created_for_season_when_episode_deleted(self):
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
        self.assertFalse(season_episode_history.exists())
        episode_history = self._history_for(Episode, '-')
        self.assertTrue(episode_history.exists())

    def test_related_history_created_for_actor_when_episode_deleted(self):
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
        self.assertEqual(episode_actor_history.related_field_history,
                         episode_history)
        self.assertEqual(episode_actor_history.history_diff, ['episode'])
        self.assertEqual(episode_actor_history.additional_data['episode'],
                         'Deleted Episode')

    def test_related_history_created_for_actors_when_clearing_episode_cast(
            self):
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
        self.assertEqual(episode_cast_history.history_diff, ['cast'])
        actor_updates = self._history_for(Actor, '~').filter(
            related_field_history=episode_cast_history
        )
        actor1_episode_history = actor_updates.filter(
            object_id=actor1.pk
        ).first()
        self.assertEqual(actor1_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor1_episode_history.history_diff, ['episode'])
        self.assertEqual(actor1_episode_history.additional_data['episode'],
                         'Updated Episode')
        actor2_episode_history = actor_updates.filter(
            object_id=actor2.pk
        ).first()
        self.assertEqual(actor2_episode_history.related_field_history,
                         episode_cast_history)
        self.assertEqual(actor2_episode_history.history_diff, ['episode'])
        self.assertEqual(actor2_episode_history.additional_data['episode'],
                         'Updated Episode')

    def test_related_history_for_interested_generic_foreign_key_with_generic_relation(  # noqa
            self):
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
        self.assertEqual(url_on_show_history.count(), 3)
        self.assertEqual(url_on_show_history[0].related_field_history,
                         self._history_for(Link, type_='-').first())
        self.assertEqual(url_on_show_history[0].additional_data['link'],
                         'Deleted Link')
        self.assertEqual(url_on_show_history[1].related_field_history,
                         self._history_for(Link, type_='~').first())
        self.assertEqual(url_on_show_history[1].additional_data['link'],
                         'Updated Link')
        self.assertEqual(url_on_show_history[2].related_field_history,
                         self._history_for(Link, type_='+').first())
        self.assertEqual(url_on_show_history[2].additional_data['link'],
                         'Created Link')

    def test_related_history_for_interested_generic_foreign_key_without_generic_relation(  # noqa
            self):
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
        self.assertEqual(url_on_episode_history.count(), 3)
        self.assertEqual(url_on_episode_history[0].additional_data['link'],
                         'Deleted Link')
        self.assertEqual(url_on_episode_history[1].additional_data['link'],
                         'Updated Link')
        self.assertEqual(url_on_episode_history[2].additional_data['link'],
                         'Created Link')

    @staticmethod
    def _history_for(class_, type_=None):
        result = HistoricalRecord.objects.filter(
            content_type__app_label=class_._meta.app_label,
            content_type__model=class_._meta.model_name
        )
        if type_ is not None:
            result = result.filter(history_type=type_)
        return result
