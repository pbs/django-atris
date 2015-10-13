from django.db import models

from atris.models import HistoryLogging


class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    updated_on = models.DateTimeField(auto_now=True)
    excluded_fields = ['updated_on']

    additional_data = {'where_from': 'Import'}  # default

    ignore_history_for_users = {'user_ids': [1010101],
                                'user_names': ['ignore_user']}

    history = HistoryLogging('additional_data', 'excluded_fields',
                             'ignore_history_for_users')


class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

    history = HistoryLogging(additional_data_param_name='additional_data',
                             ignore_history_for_users='ignore_history_for_users')  # noqa


class Voter(models.Model):
    choice = models.ForeignKey(Choice, related_name='voters')
    name = models.CharField(max_length=200)
