from django.core import management

from django.utils.six import StringIO
from django.utils.timezone import now

from pytest import mark

from tests.models import Poll


@mark.django_db
def test_initial_populate():
    # arrange
    Poll.objects.create(question="Will this populate?", pub_date=now())
    Poll.history.delete()
    # act
    management.call_command('populate_initial_history', auto=True)
    # assert
    assert Poll.history.count() == 1


@mark.django_db
def test_existing_objects():
    # arrange
    out = StringIO()
    Poll.objects.create(question="Will this populate?", pub_date=now())
    # act
    management.call_command('populate_initial_history', stderr=out)
    # assert
    assert Poll.history.count() == 1
    assert 'Existing history found, skipping model' in out.getvalue()
