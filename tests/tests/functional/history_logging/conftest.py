from __future__ import unicode_literals
from __future__ import print_function

from django.utils.timezone import now

from pytest import fixture

from tests.models import (
    Choice, Episode, Group, Poll, Season, Show, Voter, Writer,
)


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


@fixture
def groups():
    return (
        Group.objects.create(name='Group1'),
        Group.objects.create(name='Group2'),
        Group.objects.create(name='Group3'),
    )


def history_format_fks(ids):
    """
    Sorts a list of ids and converts to the format compatible with
    atris data
    :param ids: list of primary keys
    :return: string of concatenated ids after sort
    """
    sorted_ids = sorted([str(u) for u in ids])
    return ', '.join(sorted_ids)
