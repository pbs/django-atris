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


class TestLoggingRelatedFields(TestCase):

    def setUp(self):
        HistoricalRecord.objects.all().delete()

    def test_related_fields_and_remote_relations_logged_in_object_history(
            self):
        # arrange
        show = Show.objects.create(title='Mercy Street', description='')
        show_url_1 = Link.objects.create(
            name='PBS link',
            url='http://pbs.org/mercy-street',
            related_object=show
        )
        show_url_2 = Link.objects.create(
            name='Amazon link',
            url='http://amazon.com/mercy-street',
            related_object=show
        )
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=show,
                                         author=writer)
        actor1 = Actor.objects.create(name='McKinley Belcher III')
        actor2 = Actor.objects.create(name='Suzanne Bertish')
        episode.cast.add(actor1, actor2)
        Link.objects.create(
            name='PBS link',
            url='http://pbs.org/mercy-street-ep1',
            related_object=episode
        )
        # assert
        show_history = HistoricalRecord.objects.by_model_and_model_id(
            Show, show.pk
        ).first()
        self.assertEqual(
            show_history.data,
            {'id': str(show.pk),
             'title': 'Mercy Street',
             'description': '',
             'links': '{}, {}'.format(show_url_2.pk, show_url_1.pk),
             # Related object recorded with related_name if provided.
             'specials': str(episode.pk),
             # Related object recorded with ._meta.module_name if related_name
             # not set on relation.
             'season': ''}
        )
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        ).first()
        self.assertEqual(
            episode_history.data,
            {'id': str(episode.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': str(show.pk),
             'season': None,
             'cast': '{}, {}'.format(actor1.pk, actor2.pk),
             'author': str(writer.pk),
             'co_authors': ''}
            # Link relation not defined through GenericRelation is not logged
            # in the history of the owning object.
        )
        writer_history = HistoricalRecord.objects.by_model_and_model_id(
            Writer, writer.pk
        ).first()
        self.assertEqual(
            writer_history.data,
            {'id': str(writer.pk),
             'name': 'David Zabel',
             'work': str(episode.pk)}
        )
        actor_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor1.pk
        ).first()
        self.assertEqual(
            actor_history.data,
            {'id': str(actor1.pk),
             'name': 'McKinley Belcher III',
             'filmography': str(episode.pk)}
            # Filmography not displayed because it is in excluded fields.
        )

    def test_related_fields_and_remote_relations_logged_in_season_history(
            self):
        # arrange
        show = Show.objects.create(title='Mercy Street', description='')
        season_1 = Season.objects.create(
            title='1',
            description='Something',
            show=show
        )
        season_2 = Season.objects.create(
            title='2',
            description='Something new',
            show=show
        )
        writer_1 = Writer.objects.create(name='David Zabel')
        unknown_soldier = Episode.objects.create(title='Unknown Soldier',
                                                 description='',
                                                 season=season_1,
                                                 author=writer_1)
        writer_2 = Writer.objects.create(name='Walon Green')
        one_equal_temper = Episode.objects.create(title='One Equal Temper',
                                                  description='',
                                                  season=season_1,
                                                  author=writer_2)
        # assert
        show_history = HistoricalRecord.objects.by_model_and_model_id(
            Show, show.pk
        ).first()
        self.assertEqual(
            show_history.data,
            {'id': str(show.pk),
             'title': 'Mercy Street',
             'description': '',
             'links': '',
             'specials': '',
             # The list of child seasons does not appear until a subsequent
             # save on the show is performed. Or if the show is registered
             # as an interested field on the season.
             'season': ''}
        )
        show.save()  # A necessary extra save.
        show_history = HistoricalRecord.objects.by_model_and_model_id(
            Show, show.pk
        ).first()
        self.assertEqual(
            show_history.data,
            {'id': str(show.pk),
             'title': 'Mercy Street',
             'description': '',
             'links': '',
             'specials': '',
             'season': '{}, {}'.format(season_2.pk, season_1.pk)}
        )
        season_1_history = HistoricalRecord.objects.by_model_and_model_id(
            Season, season_1.pk
        ).first()
        self.assertEqual(
            season_1_history.data,
            {'id': str(season_1.pk),
             'title': '1',
             'description': 'Something',
             'show': str(show.pk),
             # Related object recorded with ._meta.module_name if related_name
             # not set on relation.
             'episode': ''}
        )
        season_1.save()  # A necessary extra save.
        season_1_history = HistoricalRecord.objects.by_model_and_model_id(
            Season, season_1.pk
        ).first()
        self.assertEqual(
            season_1_history.data,
            {'id': str(season_1.pk),
             'title': '1',
             'description': 'Something',
             'show': str(show.pk),
             # Related object recorded with ._meta.module_name if related_name
             # not set on relation.
             'episode': '{}, {}'
                        .format(one_equal_temper.pk, unknown_soldier.pk)}
        )
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, unknown_soldier.pk
        ).first()
        self.assertEqual(
            episode_history.data,
            {'id': str(unknown_soldier.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': None,
             'season': str(season_1.pk),
             'cast': '',
             'author': str(writer_1.pk),
             'co_authors': ''}
        )

    def test_excluded_contributions_field_doesnt_get_logged_for_writer(self):
        # arrange
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        co_author = Writer.objects.create(name='Walon Green')
        # act
        co_author.contributions.add(episode)
        # assert
        co_author_history = HistoricalRecord.objects.by_model_and_model_id(
            Writer, co_author.pk
        )
        self.assertEqual(co_author_history.count(), 1)
        self.assertEqual(co_author_history.first().history_type, '+')
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(episode_history.count(), 1)

    def test_co_authors_field_gets_logged_for_episode(self):
        # arrange
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        co_author = Writer.objects.create(name='Walon Green')
        # act
        episode.co_authors.add(co_author)
        # assert
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(episode_history.count(), 2)
        self.assertEqual(
            episode_history.first().data,
            {'id': str(episode.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': None,
             'season': None,
             'cast': '',
             'author': str(writer.pk),
             'co_authors': str(co_author.pk)}
        )
        co_author_history = HistoricalRecord.objects.by_model_and_model_id(
            Writer, co_author.pk
        )
        self.assertEqual(co_author_history.count(), 1)

    def test_removing_writer_from_episode_co_authors_is_logged(self):
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        co_author_1 = Writer.objects.create(name='Walon Green')
        co_author_2 = Writer.objects.create(name='Lisa Q. Wolfinger')
        episode.co_authors.add(co_author_1, co_author_2)
        # act
        episode.co_authors.remove(co_author_1)
        # assert
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(
            episode_history[1].data,
            {'id': str(episode.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': None,
             'season': None,
             'cast': '',
             'author': str(writer.pk),
             'co_authors': '{}, {}'.format(co_author_1.pk, co_author_2.pk)}
        )
        self.assertEqual(
            episode_history[0].data,
            {'id': str(episode.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': None,
             'season': None,
             'cast': '',
             'author': str(writer.pk),
             'co_authors': str(co_author_2.pk)}
        )

    def test_actor_filmography_tracked_when_adding_actors_to_cast(self):
        # arrange
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        actor1 = Actor.objects.create(name='McKinley Belcher III')
        actor2 = Actor.objects.create(name='Suzanne Bertish')
        # act
        episode.cast.add(actor1, actor2)
        # assert
        actor1_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor1.pk
        )
        self.assertEqual(actor1_history.count(), 2)
        self.assertEqual(
            actor1_history[0].data,
            {'id': str(actor1.pk),
             'name': 'McKinley Belcher III',
             'filmography': str(episode.pk)}
        )
        actor2_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor2.pk
        )
        self.assertEqual(actor2_history.count(), 2)
        self.assertEqual(
            actor2_history[0].data,
            {'id': str(actor2.pk),
             'name': 'Suzanne Bertish',
             'filmography': str(episode.pk)}
        )
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(episode_history.count(), 2)

    def test_actor_filmography_tracked_in_history_when_removing_actors_from_cast(  # noqa
            self):
        # arrange
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        actor1 = Actor.objects.create(name='McKinley Belcher III')
        actor2 = Actor.objects.create(name='Suzanne Bertish')
        episode.cast.add(actor1, actor2)
        # act
        episode.cast.remove(actor2)
        # assert
        actor1_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor1.pk
        )
        self.assertEqual(actor1_history.count(), 3)
        self.assertEqual(
            actor1_history[0].data,
            {'id': str(actor1.pk),
             'name': 'McKinley Belcher III',
             'filmography': str(episode.pk)}
        )
        actor2_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor2.pk
        )
        self.assertEqual(actor2_history.count(), 3)
        self.assertEqual(
            actor2_history[1].data,
            {'id': str(actor2.pk),
             'name': 'Suzanne Bertish',
             'filmography': str(episode.pk)}
        )
        self.assertEqual(
            actor2_history[0].data,
            {'id': str(actor2.pk),
             'name': 'Suzanne Bertish',
             'filmography': ''}
        )
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(episode_history.count(), 3)

    def test_actor_filmography_tracked_in_history_when_clearing_actors_from_cast(  # noqa
            self):
        # arrange
        writer = Writer.objects.create(name='David Zabel')
        episode = Episode.objects.create(title='Unknown Soldier',
                                         description='',
                                         show=None,
                                         author=writer)
        actor1 = Actor.objects.create(name='McKinley Belcher III')
        actor2 = Actor.objects.create(name='Suzanne Bertish')
        episode.cast.add(actor1, actor2)
        # act
        episode.cast.clear()
        # assert
        actor1_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor1.pk
        )
        self.assertEqual(actor1_history.count(), 3)
        self.assertEqual(
            actor1_history[0].data,
            {'id': str(actor1.pk),
             'name': 'McKinley Belcher III',
             'filmography': ''}
        )
        actor2_history = HistoricalRecord.objects.by_model_and_model_id(
            Actor, actor2.pk
        )
        self.assertEqual(actor2_history.count(), 3)
        self.assertEqual(
            actor2_history[0].data,
            {'id': str(actor2.pk),
             'name': 'Suzanne Bertish',
             'filmography': ''}
        )
        episode_history = HistoricalRecord.objects.by_model_and_model_id(
            Episode, episode.pk
        )
        self.assertEqual(episode_history.count(), 3)
        self.assertEqual(
            episode_history[0].data,
            {'id': str(episode.pk),
             'title': 'Unknown Soldier',
             'description': '',
             'show': None,
             'season': None,
             'cast': '',
             'author': str(writer.pk),
             'co_authors': ''}
        )


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
