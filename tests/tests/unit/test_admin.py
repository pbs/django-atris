from django.contrib.admin import site
from django.contrib.auth.models import User
from django.db.models import Count
from django.test import RequestFactory
from pytest import mark

from atris.admin import ApproxCountPaginator
from atris.models import ArchivedHistoricalRecord, HistoricalRecord
from tests.factories import (
    ArchivedHistoricalRecordFactory,
    HistoricalRecordFactory,
)


@mark.django_db
def test_small_unfiltered_table_returns_the_exact_count():
    """
    `reltuples` is unreliable for small tables and is -1 on PostgreSQL 14+
    until the table is analyzed, so small tables must use `COUNT(*)`.
    """
    # arrange
    HistoricalRecordFactory.create_batch(size=3)
    # act
    paginator = ApproxCountPaginator(HistoricalRecord.objects.all(), 2)
    # assert
    assert paginator.count == 3
    assert paginator.num_pages == 2


@mark.django_db
def test_filtered_queryset_returns_the_exact_count():
    # arrange
    HistoricalRecordFactory.create_batch(size=2, history_type=HistoricalRecord.CREATE)
    HistoricalRecordFactory.create_batch(size=3, history_type=HistoricalRecord.UPDATE)
    queryset = HistoricalRecord.objects.filter(history_type=HistoricalRecord.CREATE)
    # act
    paginator = ApproxCountPaginator(queryset, 10)
    # assert
    assert ApproxCountPaginator._is_unfiltered(queryset) is False
    assert paginator.count == 2


@mark.django_db
def test_is_unfiltered_recognizes_an_untouched_queryset():
    assert ApproxCountPaginator._is_unfiltered(HistoricalRecord.objects.all()) is True


@mark.django_db
@mark.parametrize(
    "queryset_func",
    [
        lambda: HistoricalRecord.objects.filter(
            history_type=HistoricalRecord.CREATE,
        ),
        lambda: HistoricalRecord.objects.all()[:5],
        lambda: HistoricalRecord.objects.distinct("id"),
        lambda: HistoricalRecord.objects.values("history_type").annotate(
            total=Count("id"),
        ),
    ],
    ids=["filtered", "sliced", "distinct", "grouped"],
)
def test_is_unfiltered_rejects_constrained_querysets(queryset_func):
    assert ApproxCountPaginator._is_unfiltered(queryset_func()) is False


@mark.django_db
def test_large_unfiltered_table_uses_the_approximate_count(mocker):
    """
    Proves the fast path is reachable without needing a 10k row fixture.
    """
    # arrange
    HistoricalRecordFactory.create_batch(size=2)
    queryset = HistoricalRecord.objects.all()
    mocker.patch.object(queryset, "approx_count", return_value=50000)
    # act
    paginator = ApproxCountPaginator(queryset, 100)
    # assert
    assert paginator.count == 50000
    assert paginator.num_pages == 500


@mark.django_db
def test_unknown_reltuples_falls_back_to_the_exact_count(mocker):
    """
    PostgreSQL 14+ reports -1 for a table that has never been analyzed.
    """
    # arrange
    HistoricalRecordFactory.create_batch(size=3)
    queryset = HistoricalRecord.objects.all()
    mocker.patch.object(queryset, "approx_count", return_value=-1)
    # act
    paginator = ApproxCountPaginator(queryset, 10)
    # assert
    assert paginator.count == 3


@mark.django_db
def test_count_just_below_the_threshold_falls_back_to_the_exact_count(mocker):
    # arrange
    HistoricalRecordFactory.create_batch(size=3)
    queryset = HistoricalRecord.objects.all()
    mocker.patch.object(
        queryset,
        "approx_count",
        return_value=ApproxCountPaginator.approx_count_min - 1,
    )
    # act
    paginator = ApproxCountPaginator(queryset, 10)
    # assert
    assert paginator.count == 3


@mark.django_db
def test_archived_historical_records_are_counted_separately(mocker):
    """
    `ApproxCountPaginator` is inherited by `ArchivedHistoricalRecordAdmin`, and
    the two models use separate tables.
    """
    # arrange
    ArchivedHistoricalRecordFactory.create_batch(size=2)
    queryset = ArchivedHistoricalRecord.objects.all()
    # act
    paginator = ApproxCountPaginator(queryset, 10)
    # assert
    assert paginator.count == 2
    mocker.patch.object(queryset, "approx_count", return_value=70000)
    assert ApproxCountPaginator(queryset, 10).count == 70000


def test_non_queryset_object_list_is_counted_with_len():
    """
    A plain sequence has no `approx_count`, so the paginator must not break.
    """
    paginator = ApproxCountPaginator(["a", "b", "c"], 2)

    assert paginator.count == 3


@mark.django_db
def test_admin_classes_use_the_approximate_paginator():
    from atris.admin import ArchivedHistoricalRecordAdmin, HistoricalRecordAdmin

    assert HistoricalRecordAdmin.paginator is ApproxCountPaginator
    assert ArchivedHistoricalRecordAdmin.paginator is ApproxCountPaginator


@mark.django_db
def test_admin_changelist_uses_the_paginator_and_reports_the_exact_count():
    """
    Exercises the real `ChangeList` path rather than the paginator alone, so
    that the `paginator` attribute is proven to be picked up end to end.
    """
    # arrange
    HistoricalRecordFactory.create_batch(size=3)
    model_admin = site._registry[HistoricalRecord]
    request = RequestFactory().get("/admin/atris/historicalrecord/")
    request.user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="pass",  # nosec B106
    )
    # act
    changelist = model_admin.get_changelist_instance(request)
    # assert
    assert isinstance(changelist.paginator, ApproxCountPaginator)
    assert changelist.result_count == 3
