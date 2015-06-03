from django.db import models

from atris.models import HistoryLogging


class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    updated_on = models.DateTimeField(auto_now=True)
    excluded_fields = ['updated_on']

    additional_data = {'where_from': 'Import'}  # default

    history = HistoryLogging(additional_data=additional_data,
                             excluded_fields=excluded_fields)


class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

    history = HistoryLogging()


class Voter(models.Model):
    choice = models.ForeignKey(Choice, related_name='voters')
    name = models.CharField(max_length=200)
