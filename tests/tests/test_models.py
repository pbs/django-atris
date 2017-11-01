# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from unittest import TestCase
from django.utils import six

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from django.utils.timezone import now

from atris.models import HistoricalRecord
from tests.models import (
    Poll, Choice, Voter, Show, Season, Actor, Writer, Episode, Link
)


str = unicode if six.PY2 else str


class TestModelsBasicFunctionality(TestCase):

    def setUp(self):
        self.poll = Poll.objects.create(question='question', pub_date=now())
        self.choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_1',
            votes=0
        )
        self.voter = Voter.objects.create(
            choice=self.choice,
            name='voter_1'
        )

    def tearDown(self):
        HistoricalRecord.objects.all().delete()
        Choice.objects.all().delete()
        Poll.objects.all().delete()
        Voter.objects.all().delete()

    def test_history_create_for_tracked_models(self):
        self.assertEquals(self.choice.id,
                          self.choice.history.last().object_id)
        self.assertEquals('+', self.choice.history.last().history_type)
        self.assertEquals(str(self.choice.poll_id),
                          self.choice.history.last().data['poll'])

        self.assertEquals(self.poll.id,
                          self.poll.history.last().object_id)
        self.assertEquals('+', self.poll.history.last().history_type)
        self.assertEquals(self.poll.question,
                          self.poll.history.last().data['question'])
        self.assertEquals(0, HistoricalRecord.objects.by_model(Voter).count())

    def test_history_update_for_tracked_models(self):
        self.poll.question = 'updated_question'
        self.poll.save()

        self.choice.choice = 'updated_choice'
        self.choice.save()

        self.assertEquals(2, self.poll.history.count())
        self.assertEquals(self.poll.question,
                          self.poll.history.first().data['question'])
        self.assertEquals(
            'Updated question',
            self.poll.history.first().get_diff_to_prev_string()
        )
        self.assertEquals(['question'],
                          self.poll.history.most_recent().history_diff)
        self.assertEquals('~', self.poll.history.first().history_type)

        self.assertEquals(2, self.choice.history.count())
        self.assertEquals(self.choice.choice,
                          self.choice.history.first().data['choice'])
        self.assertEquals(set(['choice', 'voters']),
                          set(self.choice.history.most_recent().history_diff))
        self.assertEquals(
            'Updated Voters, choice',
            self.choice.history.first().get_diff_to_prev_string()
        )
        self.assertEquals('~', self.choice.history.first().history_type)

        new_poll = Poll.objects.create(question='question', pub_date=now())

        self.choice.poll = new_poll
        self.choice.choice = 'second_update'
        self.choice.save()

        self.assertEquals(3, self.choice.history.count())
        self.assertEquals(str(self.choice.poll_id),
                          self.choice.history.first().data['poll'])
        self.assertEquals(
            'Updated choice, poll',
            self.choice.history.first().get_diff_to_prev_string()
        )
        self.assertEquals(set(['poll', 'choice']),
                          set(self.choice.history.most_recent().history_diff))
        self.assertEquals('~', self.poll.history.first().history_type)

    def test_history_delete_for_tracked_models(self):
        poll = Poll.objects.create(question='question', pub_date=now())

        choice = Choice.objects.create(
            poll=poll,
            choice='choice_1',
            votes=0
        )
        voter = Voter.objects.create(
            choice=choice,
            name='voter_1'
        )

        self.assertEquals(1, poll.history.count())
        self.assertEquals(1, choice.history.count())

        poll_id = poll.id
        choice_id = choice.id
        voter_id = voter.id

        choice.delete()
        poll.delete()
        voter.delete()

        self.assertEquals(2, HistoricalRecord.objects.by_model_and_model_id(
            Poll, poll_id).count())

        self.assertEquals(2, HistoricalRecord.objects.by_model_and_model_id(
            Choice, choice_id).count())

        self.assertEquals(0, HistoricalRecord.objects.by_model_and_model_id(
            Voter, voter_id).count())

    def test_default_additional_data_persists_for_valid_models(self):
        sentinel = object()
        self.assertNotEquals(sentinel,
                             getattr(self.poll, 'additional_data', sentinel))

        self.assertEquals('Import', self.poll.additional_data['where_from'])
        self.assertEquals(sentinel,
                          getattr(self.choice, 'additional_data', sentinel))
        self.assertEquals(sentinel,
                          getattr(self.voter, 'additional_data', sentinel))

    def test_explicitly_set_additional_data_persists(self):
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_2',
            votes=0
        )
        self.assertEquals(0, len(choice.history.first().additional_data))
        choice.additional_data = {'where_from': 'System'}
        # a change should be made for the history to be logged
        choice.votes = 1
        choice.save()
        self.assertEquals(2, choice.history.count())
        self.assertEquals('System',
                          choice.history.first().additional_data['where_from'])

    def test_all_wanted_fields_are_present(self):
        # make sure we cover local fields, many-to-many fields and
        # related objects
        choice_fields_len = len(Choice._meta.get_fields())
        choice_history_data_len = len(self.choice.history.first().data)
        self.assertEquals(choice_fields_len, choice_history_data_len)

    def test_history_not_generated_if_no_fields_changed(self):
        # arrange
        lastest_history = self.poll.history.first()
        previous_history_count = self.poll.history.count()
        # act
        self.poll.save()
        # assert
        self.assertEqual(self.poll.history.first(), lastest_history)
        self.assertEqual(self.poll.history.count(), previous_history_count)

    def test_excluded_fields_are_absent(self):
        poll_fields = Poll._meta.get_fields()
        history_poll_fields = self.poll.history.first().data
        self.assertTrue(Poll.excluded_fields[0]
                        not in [field for field in history_poll_fields])
        self.assertEquals(len(poll_fields) - len(Poll.excluded_fields),
                          len(history_poll_fields))

    def test_explicit_user_is_picked_up(self):
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        self.assertIsNone(choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)
        choice.history_user = User(username='test_user')
        # a change should be made for the history to be logged
        choice.votes = 1
        choice.save()
        self.assertEquals('test_user', choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)
        choice.history_user = User(id=1, username='test_user_2')
        # a change should be made for the history to be logged
        choice.votes = 2
        choice.save()
        self.assertEquals('test_user_2', choice.history.first().history_user)
        self.assertEquals(1, choice.history.first().history_user_id)

    def test_history_user_uses_user_available_info_priority(self):
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        self.assertIsNone(choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)

        # If all the info regarding user is available, the full name
        # should be used as the history_user string as a priority.
        choice.history_user = User(username='test_user', first_name='John',
                                   last_name='Doe', email='john.doe@mail.com')
        # a change should be made for the history to be logged
        choice.votes = 1
        choice.save()
        self.assertEquals('John Doe', choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)

        # If only the email and username are provided, the email should be used
        choice.history_user = User(id=1, email='john.doe@mail.com',
                                   username='test_user_2')
        # a change should be made for the history to be logged
        choice.votes = 2
        choice.save()
        self.assertEquals('john.doe@mail.com',
                          choice.history.first().history_user)
        self.assertEquals(1, choice.history.first().history_user_id)

        # When only the user name is provided, use that.
        choice.history_user = User(id=1, username='test_user_2')
        # a change should be made for the history to be logged
        choice.votes = 3
        choice.save()
        self.assertEquals('test_user_2', choice.history.first().history_user)
        self.assertEquals(1, choice.history.first().history_user_id)

    def test_diff_string_for_no_previous_history_and_not_created(self):
        created_snapshot = self.choice.history.first()
        self.assertEquals('Created Choice',
                          created_snapshot.get_diff_to_prev_string())

    def test_diff_string_works_properly_with_lost_history(self):
        """
        Since old history deletion is a thing, the situation arises that
        history that once had a previous state no longer does and the snapshot
        isn't a "creation" snapshot. In this case, the diff string can't know
        what the difference to the previous state is, so it would return
        'No prior information available.'.

        """
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        self.assertEquals('Created Choice',
                          choice.history.first().get_diff_to_prev_string())

        # Delete the history
        choice.history.delete()

        # Update with no prior history information available
        choice.choice = 'choice_1'
        choice.save()

        self.assertEquals(
            'No prior information available.',
            choice.history.first().get_diff_to_prev_string(),
            'Should not have the info required to build the history diff.'
        )

        # Check for entries that have no pre-populated history
        hist = choice.history.most_recent()
        hist.history_diff = None
        hist.save()

        self.assertEquals(
            'No prior information available.',
            choice.history.first().get_diff_to_prev_string(),
            "Shouldn't be able to generate diff."
        )

    def test_history_diff_is_generated_if_none(self):
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        self.assertEquals('Created Choice',
                          choice.history.first().get_diff_to_prev_string())

        choice.choice = 'choice_1'
        choice.save()
        # Simulate not having history_diff generated already (None)
        choice_hist = choice.history.most_recent()
        choice_hist.history_diff = None
        choice_hist.save()

        # Make sure it's None before rebuild
        self.assertIsNone(
            choice.history.most_recent().history_diff
        )

        # Should rebuild history_diff because it has prior history entries
        self.assertEquals(
            'Updated choice',
            choice.history.first().get_diff_to_prev_string(),
        )

        # History diff should now be populated
        self.assertEquals(
            ['choice'],
            choice.history.most_recent().history_diff
        )

    def test_users_marked_for_ignore_skip_history(self):
        # Should get ignored
        poll = Poll(question='question', pub_date=now())
        poll.history_user = User(username='ignore_user')
        poll.save()
        self.assertEquals(0, poll.history.count())

        # Shouldn't get ignored
        poll.history_user = User(username='not_ignored')
        poll.save()
        self.assertEquals(1, poll.history.count())

        # Should get ignored
        poll.history_user = User(id=1010101)
        poll.save()
        self.assertEquals(1, poll.history.count())

    def test_users_marked_for_ignore_without_ids_in_dict(self):
        Choice.ignore_history_for_users = {'user_names': ['ignore_user']}
        choice = Choice(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        choice.history_user = User(username='ignore_user')
        choice.save()
        self.assertEquals(0, choice.history.count())

    def test_users_marked_for_ignore_without_user_names_in_dict(self):
        Choice.ignore_history_for_users = {'user_ids': [1010101]}
        choice = Choice(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        choice.history_user = User(id=1010101)
        choice.save()
        self.assertEquals(0, choice.history.count())


class TestHistoryLoggingOrdering(TestCase):

    def test_global_history_is_ordered_by_history_date(self):
        # clear the history state prior to test starting
        HistoricalRecord.objects.all().delete()
        polls = []
        choices = []
        for i in range(10):
            poll = Poll.objects.create(question='question_{}'.format(i),
                                       pub_date=now())
            choice = Choice.objects.create(poll=poll,
                                           choice='choice_{}'.format(i),
                                           votes=0)
            polls.append(poll)
            choices.append(choice)

        self.assertEquals(len(polls + choices),
                          HistoricalRecord.objects.all().count())

        for i in range(10):
            polls[i].question += '_updated'
            polls[i].save()
            choices[i].choice += '_updated'
            choices[i].save()

        self.assertEquals(
            len(polls + choices) * 2,  # take updates into account
            HistoricalRecord.objects.all().count()
        )

        oldest_twenty_history_entries = HistoricalRecord.objects.all()[20:]
        for entry in oldest_twenty_history_entries:
            self.assertEquals('+', entry.history_type)

        newest_twenty_history_entries = HistoricalRecord.objects.all()[:20]
        for entry in newest_twenty_history_entries:
            self.assertEquals('~', entry.history_type)

    def test_model_history_is_ordered_by_history_date(self):
        # clear the history state prior to test starting
        HistoricalRecord.objects.all().delete()
        polls = []
        choices = []
        for i in range(10):
            poll = Poll.objects.create(question='question_{}'.format(i),
                                       pub_date=now())
            choice = Choice.objects.create(poll=poll,
                                           choice='choice_{}'.format(i),
                                           votes=0)
            polls.append(poll)
            choices.append(choice)

        self.assertEquals(len(polls + choices),
                          HistoricalRecord.objects.all().count())

        for i in range(10):
            polls[i].question += '_updated'
            polls[i].save()
            choices[i].choice += '_updated'
            choices[i].save()

        self.assertEquals(
            len(polls + choices) * 2,  # take updates into account
            HistoricalRecord.objects.all().count()
        )

        oldest_ten_model_history_entries = Poll.history.all()[10:]

        for entry in oldest_ten_model_history_entries:
            self.assertEquals('+', entry.history_type)

        newest_ten_model_history_entries = Poll.history.all()[:10]
        for entry in newest_ten_model_history_entries:
            self.assertEquals('~', entry.history_type)

        self.assertEquals('+', Choice.history.last().history_type)
        self.assertEquals('~', Choice.history.first().history_type)

    def test_model_instance_history_is_ordered_by_history_date(self):
        poll = Poll.objects.create(question='question',
                                   pub_date=now())

        poll.question += '_updated'
        poll.save()

        self.assertEquals('+', poll.history.last().history_type)
        self.assertEquals('~', poll.history.first().history_type)


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


class TestHistoricalRecordQuerySet(TestCase):

    def tearDown(self):
        HistoricalRecord.objects.all().delete()

    def test_get_records_by_app_label_and_model_name_returns_specific_entries(
            self):
        # arrange
        weather = Poll.objects.create(question='How is the weather?',
                                      pub_date=now())
        dinner = Poll.objects.create(question='What is for dinner',
                                     pub_date=now())
        dinner.question = "What's for dinner?"
        dinner.save()
        weather.delete()
        ham = Choice.objects.create(poll=dinner, choice='Ham & eggs', votes=0)
        Voter.objects.create(choice=ham, name='John')
        # act
        result = HistoricalRecord.objects.by_app_label_and_model_name(
            Poll._meta.app_label, Poll._meta.model_name
        )
        # assert
        assert result.count() == 4
        poll_content_type = ContentType.objects.get_for_model(Poll)
        by_content_type = result.filter(content_type=poll_content_type)
        assert by_content_type.filter(history_type='+').count() == 2
        assert by_content_type.filter(history_type='-').count() == 1
        assert by_content_type.filter(history_type='~').count() == 1

    def test_no_records_by_app_label_and_model_name_returned(self):
        # arrange
        Poll.objects.create(question='How is the weather?', pub_date=now())
        # act
        result = HistoricalRecord.objects.by_app_label_and_model_name(
            Choice._meta.app_label, Choice._meta.model_name
        )
        # assert
        assert result.exists() is False
