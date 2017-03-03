# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from unittest import TestCase
from django.utils import six

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from django.utils.timezone import now

from atris.models import HistoricalRecord
from tests.models import Poll, Choice, Voter


str = unicode if six.PY2 else str


class TestModelsBasicFunctionality(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.poll = Poll.objects.create(question='question', pub_date=now())

        cls.choice = Choice.objects.create(
            poll=cls.poll,
            choice='choice_1',
            votes=0
        )
        cls.voter = Voter.objects.create(
            choice=cls.choice,
            name='voter_1'
        )

    def test_history_create_for_tracked_models(self):
        self.assertEquals(self.choice.id,
                          self.choice.history.last().object_id)
        self.assertEquals('+', self.choice.history.last().history_type)
        self.assertEquals(str(self.choice.poll_id),
                          self.choice.history.last().data['poll_id'])

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
        self.assertEquals(['choice'],
                          self.choice.history.most_recent().history_diff)
        self.assertEquals(
            'Updated choice',
            self.choice.history.first().get_diff_to_prev_string()
        )
        self.assertEquals('~', self.choice.history.first().history_type)

        new_poll = Poll.objects.create(question='question', pub_date=now())

        self.choice.poll = new_poll
        self.choice.choice = 'second_update'
        self.choice.save()

        self.assertEquals(3, self.choice.history.count())
        self.assertEquals(str(self.choice.poll_id),
                          self.choice.history.first().data['poll_id'])
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
        choice.save()
        self.assertEquals(2, choice.history.count())
        self.assertEquals('System',
                          choice.history.first().additional_data['where_from'])

    def test_all_wanted_fields_are_present(self):
        choice_fields_len = len(Choice._meta.fields)
        choice_history_data_len = len(self.choice.history.first().data)
        self.assertEquals(choice_fields_len, choice_history_data_len)

    def test_excluded_fields_are_absent(self):
        poll_fields = Poll._meta.fields
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
        choice.save()
        self.assertEquals('test_user', choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)
        choice.history_user = User(id=1, username='test_user_2')
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
        choice.save()
        self.assertEquals('John Doe', choice.history.first().history_user)
        self.assertIsNone(choice.history.first().history_user_id)

        # If only the email and username are provided, the email should be used
        choice.history_user = User(id=1, email='john.doe@mail.com',
                                   username='test_user_2')
        choice.save()
        self.assertEquals('john.doe@mail.com',
                          choice.history.first().history_user)
        self.assertEquals(1, choice.history.first().history_user_id)

        # When only the user name is provided, use that.
        choice.history_user = User(id=1, username='test_user_2')
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

    def test_updated_with_no_change(self):
        choice = Choice.objects.create(
            poll=self.poll,
            choice='choice_3',
            votes=0
        )
        self.assertEquals('Created Choice',
                          choice.history.first().get_diff_to_prev_string())
        choice.save()
        self.assertEquals('Updated with no change',
                          choice.history.first().get_diff_to_prev_string())

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

        self.assertEquals(
            # Add twice the number of choices created because of the additional
            # related object history created for polls because of choices.
            len(polls) + 2 * len(choices),
            HistoricalRecord.objects.all().count()
        )

        for i in range(10):
            polls[i].question += '_updated'
            polls[i].save()
            choices[i].choice += '_updated'
            choices[i].save()

        self.assertEquals(
            2 * len(polls) + 4 * len(choices),  # take updates into account
            HistoricalRecord.objects.all().count()
        )
        # assert
        oldest_30_history_entries = HistoricalRecord.objects.values_list(
            'content_type__model', 'history_type')[30:]
        self.assertEqual(
            list(oldest_30_history_entries),
            [('poll', '~'), ('choice', '+'), ('poll', '+')] * 10
        )
        newest_30_history_entries = HistoricalRecord.objects.values_list(
            'content_type__model', 'history_type')[:30]
        self.assertEqual(
            list(newest_30_history_entries),
            [('poll', '~'), ('choice', '~'), ('poll', '~')] * 10
        )

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
        for i in range(10):
            polls[i].question += '_updated'
            polls[i].save()
            choices[i].choice += '_updated'
            choices[i].save()
        # assert
        oldest_20_model_history_entries = Poll.history.values_list(
            'history_type', flat=True)[20:]
        self.assertEqual(
            list(oldest_20_model_history_entries), ['~', '+'] * 10)
        newest_20_model_history_entries = Poll.history.values_list(
            'history_type', flat=True)[:20]
        self.assertEqual(list(newest_20_model_history_entries), ['~'] * 20)
        self.assertEquals('+', Choice.history.last().history_type)
        self.assertEquals('~', Choice.history.first().history_type)

    def test_model_instance_history_is_ordered_by_history_date(self):
        poll = Poll.objects.create(question='question',
                                   pub_date=now())

        poll.question += '_updated'
        poll.save()

        self.assertEquals('+', poll.history.last().history_type)
        self.assertEquals('~', poll.history.first().history_type)


class TestRelatedHistory(TestCase):

    def setUp(self):
        HistoricalRecord.objects.all().delete()

    def test_related_history_created_for_poll_when_choice_added(self):
        # arrange
        dinner = Poll.objects.create(question="What's for dinner?",
                                     pub_date=now())
        # act
        Choice.objects.create(poll=dinner, choice='Ham & eggs', votes=0)
        # assert
        ham_history = HistoricalRecord.objects.get(
            content_type__app_label=Choice._meta.app_label,
            content_type__model=Choice._meta.model_name)
        ham_for_dinner_history = HistoricalRecord.objects.get(
            content_type__app_label=Poll._meta.app_label,
            content_type__model=Poll._meta.model_name,
            history_type='~'
        )
        assert ham_for_dinner_history.related_field_history == ham_history


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
        self.assertEqual(result.count(), 5)
        poll_content_type = ContentType.objects.get_for_model(Poll)
        by_content_type = result.filter(content_type=poll_content_type)
        self.assertEqual(by_content_type.filter(history_type='+').count(), 2)
        self.assertEqual(by_content_type.filter(history_type='-').count(), 1)
        self.assertEqual(by_content_type.filter(history_type='~').count(), 2)

    def test_no_records_by_app_label_and_model_name_returned(self):
        # arrange
        Poll.objects.create(question='How is the weather?', pub_date=now())
        # act
        result = HistoricalRecord.objects.by_app_label_and_model_name(
            Choice._meta.app_label, Choice._meta.model_name
        )
        # assert
        assert result.exists() is False
