from unittest import TestCase

from django.utils.timezone import now

from atris.models import HistoricalRecord
from atris.tests.models import Poll, Choice, Voter


class TestHistoryLogging(TestCase):
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

    def testHistoryCreateForTrackedModels(self):
        self.assertEquals(self.choice.id,
                          self.choice.history.last().object_id)
        self.assertEquals(u'+', self.choice.history.last().history_type)
        self.assertEquals(unicode(self.choice.poll_id),
                          self.choice.history.last().data['poll_id'])

        self.assertEquals(self.poll.id,
                          self.poll.history.last().object_id)
        self.assertEquals(u'+', self.poll.history.last().history_type)
        self.assertEquals(self.poll.question,
                          self.poll.history.last().data['question'])
        self.assertEquals(0, len(HistoricalRecord.objects.by_model(Voter)))

    def testHistoryUpdateForTrackedModels(self):
        self.poll.question = 'updated_question'
        self.poll.save()

        self.choice.choice = 'updated_choice'
        self.choice.save()

        self.assertEquals(2, len(self.poll.history.all()))
        self.assertEquals(self.poll.question,
                          self.poll.history.first().data['question'])
        self.assertEquals(
            'Updated Question',
            self.poll.history.first().get_superficial_diff_string()
        )

        self.assertEquals(2, len(self.choice.history.all()))
        self.assertEquals(self.choice.choice,
                          self.choice.history.first().data['choice'])
        self.assertEquals(
            'Updated Choice',
            self.choice.history.first().get_superficial_diff_string()
        )

        new_poll = Poll.objects.create(question='question', pub_date=now())

        self.choice.poll = new_poll
        self.choice.choice = 'second_update'
        self.choice.save()

        self.assertEquals(3, len(self.choice.history.all()))
        self.assertEquals(unicode(self.choice.poll_id),
                          self.choice.history.first().data['poll_id'])
        self.assertEquals(
            'Updated Poll id, Choice',
            self.choice.history.first().get_superficial_diff_string()
        )

    def testHistoryDeleteForTrackedModels(self):
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

        self.assertEquals(1, len(poll.history.all()))
        self.assertEquals(1, len(choice.history.all()))

        poll_id = poll.id
        choice_id = choice.id
        voter_id = voter.id

        choice.delete()
        poll.delete()
        voter.delete()

        self.assertEquals(2, len(
            HistoricalRecord.objects.by_model_and_model_id(Poll, poll_id)))

        self.assertEquals(2, len(HistoricalRecord.objects.by_model_and_model_id(
            Choice,
            choice_id
        )))

        self.assertEquals(0, len(
            HistoricalRecord.objects.by_model_and_model_id(Voter, voter_id)))


