

@mark.django_db
def test_diff_string_for_no_previous_history_and_not_created(setup):
    poll, choice, voter = setup
    created_snapshot = self.choice.history.first()
    self.assertEquals('Created Choice',
                      created_snapshot.get_diff_to_prev_string())


@mark.django_db
def test_diff_string_works_properly_with_lost_history(setup):
    poll, choice, voter = setup
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


@mark.django_db
def test_history_diff_is_generated_if_none(setup):
    poll, choice, voter = setup
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
