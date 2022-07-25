import random
import uuid

from datetime import datetime
from string import ascii_letters

from django.contrib.contenttypes.models import ContentType

from atris.models import ArchivedHistoricalRecord, HistoricalRecord
from atris.models.helpers import get_field_internal_type
from tests.models import (
    Actor,
    Admin,
    Choice,
    Episode,
    Episode2,
    Group,
    Link,
    Poll,
    Season,
    Show,
    Special,
    Voter,
    Writer,
)


def random_integer():
    return random.randint(1, 100000)


def random_string():
    return "".join(random.choice(ascii_letters) for _ in range(10))


class AbstractFactory:
    MODEL = None

    IGNORED_TYPES = {
        "ForeignKey",
        "GenericForeignKey",
        "ManyToManyField",
        "OneToOneField",
    }

    DEFAULT_VALUES_FOR_INTERNAL_TYPE = {
        "AutoField": lambda: random_integer(),
        "DateTimeField": lambda: datetime.now(),
        "CharField": lambda: random_string(),
        "IntegerField": lambda: random_integer(),
        "UUIDField": lambda: uuid.uuid4(),
        "PositiveIntegerField": lambda: random_integer(),
        "ArrayField": lambda: [],
        "JSONField": lambda: {},
        "BooleanField": lambda: random.choice([True, False]),
    }

    # Overrides default value for the field type
    DEFAULT_VALUES = {}

    FIELDS_NOT_SPECIFIED_BY_DEFAULT = []

    @classmethod
    def create(cls, **kwargs):

        if not cls.MODEL:
            raise NotImplementedError

        create_kwargs = {}
        create_kwargs.update(kwargs)
        for field_name, lambda_func in cls.DEFAULT_VALUES.items():
            if field_name not in create_kwargs:
                create_kwargs[field_name] = lambda_func()

        other_fields = [
            (f.name, get_field_internal_type(f))
            for f in cls.MODEL._meta.get_fields()
            if (
                f.name not in cls.FIELDS_NOT_SPECIFIED_BY_DEFAULT
                and f.name not in create_kwargs
            )
        ]

        create_kwargs.update(
            {
                field_name: cls.DEFAULT_VALUES_FOR_INTERNAL_TYPE.get(field_type)()
                for field_name, field_type in other_fields
                if field_type not in cls.IGNORED_TYPES
            }
        )

        return cls.MODEL.objects.create(**create_kwargs)

    @classmethod
    def create_batch(cls, size, **kwargs):
        return [cls.create(**kwargs) for _ in range(size)]


class HistoricalRecordFactory(AbstractFactory):
    MODEL = HistoricalRecord

    DEFAULT_VALUES = {
        "object_id": lambda: str(random_integer()),
        "history_type": lambda: random.choice(
            [
                HistoricalRecord.CREATE,
                HistoricalRecord.UPDATE,
                HistoricalRecord.DELETE,
            ]
        ),
        "content_type": lambda: random.choice(
            [ct for ct in ContentType.objects.all()],
        ),
    }

    FIELDS_NOT_SPECIFIED_BY_DEFAULT = [
        "history_date",
    ]


class ArchivedHistoricalRecordFactory(HistoricalRecordFactory):
    MODEL = ArchivedHistoricalRecord


class ActorFactory(AbstractFactory):
    MODEL = Actor


class AdminFactory(AbstractFactory):
    MODEL = Admin


class ChoiceFactory(AbstractFactory):
    MODEL = Choice


class EpisodeFactory(AbstractFactory):
    MODEL = Episode


class Episode2Factory(AbstractFactory):
    MODEL = Episode2


class GroupFactory(AbstractFactory):
    MODEL = Group


class LinkFactory(AbstractFactory):
    MODEL = Link

    DEFAULT_VALUES = {
        "content_type": lambda: random.choice(
            [ct for ct in ContentType.objects.all()],
        ),
    }


class PollFactory(AbstractFactory):
    MODEL = Poll


class SeasonFactory(AbstractFactory):
    MODEL = Season


class ShowFactory(AbstractFactory):
    MODEL = Show


class SpecialFactory(AbstractFactory):
    MODEL = Special


class VoterFactory(AbstractFactory):
    MODEL = Voter


class WriterFactory(AbstractFactory):
    MODEL = Writer
