# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from django.utils import six

str = str if six.PY2 else str

from unittest import TestCase
from django.contrib.auth.models import User

from django.utils.timezone import now

from src.atris.models import HistoricalRecord
from tests.models import Poll, Choice, Voter


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
            'Updated Question',
            self.poll.history.first().get_diff_to_prev_string()
        )
        self.assertEquals('~', self.poll.history.first().history_type)

        self.assertEquals(2, self.choice.history.count())
        self.assertEquals(self.choice.choice,
                          self.choice.history.first().data['choice'])
        self.assertEquals(
            'Updated Choice',
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
            'Updated Poll id, Choice',
            self.choice.history.first().get_diff_to_prev_string()
        )
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

        self.assertEquals(len(polls + choices) * 2,  # take updates into account
                          HistoricalRecord.objects.all().count())

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

        self.assertEquals(len(polls + choices) * 2,  # take updates into account
                          HistoricalRecord.objects.all().count())

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
