from __future__ import unicode_literals
from __future__ import print_function

from django.utils.timezone import now

from pytest import fixture

from tests.models import Poll, Choice, Voter


@fixture
def poll():
    return Poll.objects.create(question='question', pub_date=now())


@fixture
def choice(poll):
    return Choice.objects.create(poll=poll, choice='choice_1', votes=0)


@fixture
def voter(choice):
    return Voter.objects.create(choice=choice, name='voter_1')
