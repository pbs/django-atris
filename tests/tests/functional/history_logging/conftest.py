from __future__ import unicode_literals
from __future__ import print_function

from django.utils.timezone import now

from pytest import fixture

from tests.models import Poll, Choice, Voter, Show, Writer, Episode, Season


@fixture
def poll():
    return Poll.objects.create(question='question', pub_date=now())


@fixture
def choice(poll):
    return Choice.objects.create(poll=poll, choice='choice_1', votes=0)


@fixture
def voter(choice):
    return Voter.objects.create(choice=choice, name='voter_1')


@fixture
def show():
    return Show.objects.create(title='Mercy Street', description='')


@fixture
def writer():
    return Writer.objects.create(name='David Zabel')


@fixture
def episode(show, writer):
    episode = Episode.objects.create(title='Unknown Soldier',
                                     description='',
                                     show=show,
                                     author=writer)
    return episode


@fixture
def season(show):
    return Season.objects.create(title='1', description='Something', show=show)
