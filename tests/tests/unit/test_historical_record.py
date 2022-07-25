import re

from django.contrib.contenttypes.models import ContentType
from pytest import fixture, mark, raises

from atris.models import HistoricalRecord, get_history_model
from tests.factories import EpisodeFactory, HistoricalRecordFactory, WriterFactory
from tests.models import Choice, Poll


@fixture
def poll_content_type():
    return ContentType.objects.get_for_model(Poll)


@fixture
def choice_content_type():
    return ContentType.objects.get_for_model(Choice)


@fixture
def poll_history_setup(poll_content_type):
    return HistoricalRecordFactory.create_batch(
        size=3,
        content_type=poll_content_type,
    )


@fixture
def choice_history_setup(choice_content_type):
    return HistoricalRecordFactory.create_batch(
        size=3,
        content_type=choice_content_type,
    )


@fixture
def history_setup(poll_history_setup, choice_history_setup):
    return poll_history_setup + choice_history_setup


@mark.django_db
class TestDiffString:
    def test_diff_string_for_create(self, poll_content_type):
        # arrange
        create_history = HistoricalRecordFactory.create(
            content_type=poll_content_type,
            history_type=HistoricalRecord.CREATE,
        )
        # act
        result = create_history.get_diff_to_prev_string()
        # assert
        assert result == "Created poll"

    def test_diff_string_for_delete(self, poll_content_type):
        # arrange
        delete_history = HistoricalRecordFactory.create(
            content_type=poll_content_type,
            history_type=HistoricalRecord.DELETE,
        )
        # act
        result = delete_history.get_diff_to_prev_string()
        # assert
        assert result == "Deleted poll"

    def test_diff_string_for_update_with_one_field_updated(self, poll_content_type):
        # arrange
        update_history = HistoricalRecordFactory.create(
            content_type=poll_content_type,
            history_type=HistoricalRecord.UPDATE,
            history_diff=["question"],
        )
        # act
        result = update_history.get_diff_to_prev_string()
        # assert
        assert result == "Updated question"

    def test_diff_string_for_update_with_more_fields_updated(self, poll_content_type):
        # arrange
        update_history = HistoricalRecordFactory.create(
            content_type=poll_content_type,
            history_type=HistoricalRecord.UPDATE,
            history_diff=["question", "pub_date"],
        )
        # act
        result = update_history.get_diff_to_prev_string()
        # assert
        expected_words = set(re.split(r"\W+", result))
        assert expected_words == {"Updated", "date", "published", "question"}

    def test_diff_string_works_properly_with_lost_history(self, poll_content_type):
        """
        Since old history deletion is a thing, the situation arises that
        history that once had a previous state no longer does and the snapshot
        isn't a "creation" snapshot. In this case, the diff string can't know
        what the difference to the previous state is, so it would return
        'No prior information available.'.

        """
        # arrange
        update_without_previous = HistoricalRecordFactory.create(
            id=1,
            object_id="1",
            content_type=poll_content_type,
            history_type=HistoricalRecord.UPDATE,
            history_diff=None,
        )
        update_with_previous = HistoricalRecordFactory.create(
            id=2,
            object_id="1",
            content_type=poll_content_type,
            history_type=HistoricalRecord.UPDATE,
            history_diff=None,
        )
        # act
        without_previous = update_without_previous.get_diff_to_prev_string()
        with_previous = update_with_previous.get_diff_to_prev_string()
        # assert
        message = "Should not have the info required to build the history diff."
        assert without_previous == "No prior information available.", message
        assert with_previous == "Updated with no change", message

    def test_diff_string_for_non_existent_field(self):
        # arrange
        event_with_non_existent_field_in_diff = HistoricalRecordFactory.create(
            history_type=HistoricalRecord.UPDATE,
            history_diff=["non_existent_field"],
        )
        # act
        diff = event_with_non_existent_field_in_diff.get_diff_to_prev_string()
        # assert
        assert diff == "Updated Non Existent Field"

    def test_diff_string_for_field_with_no_verbose_name(
        self, mocker, poll_content_type
    ):
        # django automatically creates verbose names for fields
        # a mock object is required

        # arrange
        field_name = "field_with_no_verbose_name"
        event_no_verbose_name_field_in_diff = HistoricalRecordFactory.create(
            content_type=poll_content_type,
            history_type=HistoricalRecord.UPDATE,
            # adding field_name to history diff is not required
            # the only requirement is to have a non-empty history diff
            history_diff=[field_name],
        )

        mocked_field_object = mocker.Mock()
        mocked_field_object.name = "field_with_no_verbose_name"
        del mocked_field_object.verbose_name

        mocker.patch(
            "tests.models.Poll._meta.get_field",
            return_value=mocked_field_object,
        )
        # act
        diff = event_no_verbose_name_field_in_diff.get_diff_to_prev_string()
        # assert
        assert diff == "Updated Field With No Verbose Name"


@mark.django_db
class TestHistoryLoggingOrdering:
    def test_global_history_is_ordered_by_date(self, history_setup):
        expected = list(reversed(history_setup))
        assert list(HistoricalRecord.objects.all()) == expected

    def test_model_history_is_ordered_by_date(self, history_setup):
        expected_poll_history = list(reversed(history_setup[:3]))
        assert list(Poll.history.all()) == expected_poll_history
        expected_choice_history = list(reversed(history_setup[3:]))
        assert list(Choice.history.all()) == expected_choice_history

    def test_model_instance_history_is_ordered_by_date(self):
        # arrange
        author = WriterFactory.create()

        episode = EpisodeFactory.create(author=author)
        episode.title = "modified"
        episode.save()

        episode.description = "modified"
        episode.save()

        author.delete()
        # act
        history_type_and_diff = [
            (e.history_type, e.history_diff) for e in episode.history.all()
        ]
        # assert
        assert history_type_and_diff == [
            (HistoricalRecord.DELETE, []),
            (HistoricalRecord.UPDATE, ["description"]),
            (HistoricalRecord.UPDATE, ["title"]),
            (HistoricalRecord.CREATE, []),
        ]


@mark.django_db
class TestGetHistoryModel:
    def test_get_history_model_without_settings(self):
        assert get_history_model() == HistoricalRecord

    def test_get_history_model_from_settings(self, settings):
        settings.ATRIS_HISTORY_MODEL = "atris.HistoricalRecord"
        assert get_history_model() == HistoricalRecord

    def test_get_invalid_history_model_from_settings(self, settings):
        settings.ATRIS_HISTORY_MODEL = "foo.bar"
        with raises(ContentType.DoesNotExist):
            get_history_model()


@mark.django_db
def test_str_historical_record():
    hr = HistoricalRecordFactory.create()
    expected = "{history_type} {content_type} id={object_id}".format(
        history_type=hr.get_history_type_display(),
        content_type=hr.content_type.model,
        object_id=hr.object_id,
    )
    assert str(hr) == expected
