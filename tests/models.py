import uuid

from django.contrib.contenttypes.fields import (
    ContentType,
    GenericForeignKey,
    GenericRelation,
)
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _

from atris.models import HistoryLogging


class Poll(models.Model):
    custom_id = models.AutoField(verbose_name="ID", primary_key=True)
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField(_("date published"))
    updated_on = models.DateTimeField(auto_now=True)

    excluded_fields = ["updated_on", "choices"]

    additional_data = {"where_from": "Import"}  # default

    ignore_history_for_users = {
        "user_ids": [1010101],
        "user_names": ["ignore_user"],
    }

    history = HistoryLogging(
        "additional_data",
        "excluded_fields",
        "ignore_history_for_users",
    )


class Choice(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

    class Meta:
        verbose_name = "Choice"

    history = HistoryLogging(
        additional_data_param_name="additional_data",
        ignore_history_for_users="ignore_history_for_users",
    )


class Admin(models.Model):
    uuid = models.UUIDField(
        verbose_name="ID",
        primary_key=True,
        default=uuid.uuid4,
    )
    name = models.CharField(max_length=200)


class Group(models.Model):
    name = models.CharField(max_length=200)
    admins = models.ManyToManyField(Admin, related_name="groups")

    history = HistoryLogging()


class Voter(models.Model):
    id = models.UUIDField(
        verbose_name="ID",
        primary_key=True,
        default=uuid.uuid4,
    )
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name="voters",
    )
    name = models.CharField(max_length=200)
    groups = models.ManyToManyField(Group, related_name="voters")


class Show(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)

    # Adding a related_query_name parameter to a GenericRelation will cause
    # history generation to fail
    links = GenericRelation("Link")

    history_additional_data = {"where_from": "System"}
    history = HistoryLogging(
        additional_data_param_name="history_additional_data",
    )


class Season(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)

    history = HistoryLogging(additional_data_param_name="additional_data")


class Actor(models.Model):
    name = models.CharField(max_length=100)

    history = HistoryLogging()


class Writer(models.Model):
    cid = models.UUIDField(
        verbose_name="ID",
        primary_key=True,
        default=uuid.uuid4,
    )
    name = models.CharField(max_length=100)

    excluded_fields = ["contributions"]
    history = HistoryLogging(excluded_fields_param_name="excluded_fields")


class Episode(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    show = models.ForeignKey(
        Show,
        on_delete=models.CASCADE,
        null=True,
        related_name="specials",
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        null=True,
    )
    cast = models.ManyToManyField(Actor, related_name="filmography")
    author = models.OneToOneField(
        Writer,
        on_delete=models.CASCADE,
        related_name="work",
    )
    co_authors = models.ManyToManyField(Writer, related_name="contributions")
    is_published = models.BooleanField(default=True, null=False)
    keywords = ArrayField(
        base_field=models.CharField(max_length=20, blank=True),
        null=False,
        default=lambda: [],
    )
    episode_metadata = JSONField(null=False, default=lambda: {})

    additional_data = {"where_from": "System"}
    interested_related_fields = ["show", "cast", "author"]
    excluded_fields = ["episode2"]
    history = HistoryLogging(
        excluded_fields_param_name="excluded_fields",
        additional_data_param_name="additional_data",
        interested_related_fields="interested_related_fields",
    )


class Episode2(Episode):

    groups = models.ManyToManyField(Group, related_name="episodes")

    additional_data = {"where_from": "System"}
    interested_related_fields = ["show", "cast", "author"]
    history = HistoryLogging(
        additional_data_param_name="additional_data",
        interested_related_fields="interested_related_fields",
    )


class Special(Episode):
    class Meta:
        proxy = True


class Link(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=256)
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    related_object = GenericForeignKey("content_type", "object_id")

    interested_related_fields = ["related_object"]
    history = HistoryLogging(
        interested_related_fields="interested_related_fields",
    )
