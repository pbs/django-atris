from django.contrib.contenttypes.fields import (
    ContentType, GenericRelation, GenericForeignKey
)
from django.db import models

from atris.models import HistoryLogging


class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    updated_on = models.DateTimeField(auto_now=True)

    excluded_fields = ['updated_on', 'choices']

    additional_data = {'where_from': 'Import'}  # default

    ignore_history_for_users = {'user_ids': [1010101],
                                'user_names': ['ignore_user']}

    history = HistoryLogging('additional_data', 'excluded_fields',
                             'ignore_history_for_users')


class Choice(models.Model):
    poll = models.ForeignKey(Poll, related_name='choices')
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

    class Meta:
        verbose_name = 'Choice'

    history = HistoryLogging(
        additional_data_param_name='additional_data',
        ignore_history_for_users='ignore_history_for_users'
    )


class Admin(models.Model):
    name = models.CharField(max_length=200)


class Group(models.Model):
    name = models.CharField(max_length=200)
    admins = models.ManyToManyField(Admin, related_name='groups')

    history = HistoryLogging()


class Voter(models.Model):
    choice = models.ForeignKey(Choice, related_name='voters')
    name = models.CharField(max_length=200)
    groups = models.ManyToManyField(Group, related_name='voters')


class Show(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    links = GenericRelation('Link')

    history_additional_data = {'where_from': 'System'}
    history = HistoryLogging(
        additional_data_param_name='history_additional_data')


class Season(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    show = models.ForeignKey(Show)

    history = HistoryLogging()


class Actor(models.Model):
    name = models.CharField(max_length=100)

    history = HistoryLogging()


class Writer(models.Model):
    name = models.CharField(max_length=100)

    excluded_fields = ['contributions']
    history = HistoryLogging(excluded_fields_param_name='excluded_fields')


class Episode(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    show = models.ForeignKey(Show, null=True, related_name='specials')
    season = models.ForeignKey(Season, null=True)
    cast = models.ManyToManyField(Actor, related_name='filmography')
    author = models.OneToOneField(Writer, related_name='work')
    co_authors = models.ManyToManyField(Writer, related_name='contributions')

    additional_data = {'where_from': 'System'}
    interested_related_fields = ['show', 'cast', 'author']
    excluded_fields = ['episode2']
    history = HistoryLogging(
        excluded_fields_param_name='excluded_fields',
        additional_data_param_name='additional_data',
        interested_related_fields='interested_related_fields'
    )


class Episode2(Episode):

    groups = models.ManyToManyField(Group, related_name='episodes')


class Special(Episode):

    class Meta:
        proxy = True


class Link(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=256)
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    related_object = GenericForeignKey('content_type', 'object_id')

    interested_related_fields = ['related_object']
    history = HistoryLogging(
        interested_related_fields='interested_related_fields'
    )
