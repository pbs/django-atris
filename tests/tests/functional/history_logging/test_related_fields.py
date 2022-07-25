from pytest import mark

from atris.models import HistoryLogging
from tests.conftest import history_format_fks
from tests.factories import (
    AdminFactory,
    EpisodeFactory,
    LinkFactory,
    SeasonFactory,
    ShowFactory,
    VoterFactory,
    WriterFactory,
)


@mark.django_db
def test_related_object_recorded_with_the_specified_related_name(show):
    # assert
    assert "specials" in show.history.first().data


@mark.django_db
def test_related_object_recorded_with_module_name_if_no_related_name_specified(
    show,
):
    # assert
    assert "season" in show.history.first().data


@mark.django_db
def test_changes_to_many_to_one_relations_recorded_automatically(show, episode, season):
    # assert
    season_added, episode_update_notif, special_added = show.history.all()[:3]
    assert season_added.history_type == "~"
    assert season_added.history_diff == ["season"]
    assert season_added.data["season"] == str(season.pk)
    episode_created = episode.history.first()
    assert episode_update_notif.related_field_history == episode_created
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["specials"]
    assert special_added.data["specials"] == str(episode.pk)


@mark.django_db
def test_changing_a_foreign_key_value_reflected_on_both_past_and_present_referenced_objects(  # noqa: E501
    show, season
):
    # arrange
    show2 = ShowFactory.create()
    # act
    season.show = show2
    season.save()
    # assert
    season_added = show2.history.first()
    assert season_added.history_type == "~"
    assert season_added.history_diff == ["season"]
    assert season_added.data["season"] == str(season.pk)
    season_removed = show.history.first()
    assert season_removed.history_type == "~"
    assert season_removed.history_diff == ["season"]
    assert season_removed.data["season"] == ""


@mark.django_db
def test_generic_foreign_keys_backed_by_a_generic_relation_are_recorded(show):
    # arrange
    show_url2, show_url3 = LinkFactory.create_batch(
        size=2,
        related_object=show,
    )
    # assert
    link_update_notif, link_added = show.history.all()[:2]
    assert link_update_notif.related_field_history is not None
    assert link_added.history_type == "~"
    assert link_added.history_diff == ["links"]
    expected_links = history_format_fks([show_url2.pk, show_url3.pk])
    assert link_added.data["links"] == expected_links


@mark.django_db
def test_generic_foreign_keys_not_backed_by_a_generic_relation_are_not_recorded(
    episode,
):
    # arrange
    LinkFactory.create(related_object=episode)
    # assert
    special_history = episode.history.first()
    expected_keys = {
        "id",
        "title",
        "description",
        "show",
        "season",
        "cast",
        "author",
        "co_authors",
        "is_published",
        "keywords",
        "episode_metadata",
    }  # no relation to Link
    assert set(special_history.data.keys()) == expected_keys


@mark.django_db
def test_one_to_one_relations_tracked_on_both_models(writer, episode):
    # assert
    episode_created_notif, special_added_for_writer = writer.history.all()[:2]
    assert episode_created_notif.related_field_history is not None
    assert special_added_for_writer.history_type == "~"
    assert special_added_for_writer.history_diff == ["work"]
    assert special_added_for_writer.data["work"] == str(episode.pk)
    special_created = episode.history.first()
    assert special_created.history_type == "+"
    assert special_created.data["author"] == str(writer.pk)


@mark.django_db
def test_adding_to_many_to_many_relations_recorded_on_both_sides(episode, actors):
    # arrange
    actor2, actor3 = actors
    episode.cast.add(actor3, actor2)
    # assert
    cast_updated = episode.history.first()
    assert cast_updated.history_type == "~"
    assert cast_updated.history_diff == ["cast"]
    assert cast_updated.data["cast"] == history_format_fks(
        [
            actor3.pk,
            actor2.pk,
        ]
    )
    episode_update_notif, special_added = actor3.history.all()[:2]
    assert episode_update_notif.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == str(episode.pk)
    episode_update_notif, special_added = actor2.history.all()[:2]
    assert episode_update_notif.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == str(episode.pk)


@mark.django_db
def test_removing_from_many_to_many_relations_recorded_on_both_sides(episode, actors):
    # arrange
    actor2, actor3 = actors
    episode.cast.add(actor3, actor2)
    episode.cast.remove(actor3)
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == "~"
    assert cast_updated.history_diff == ["cast"]
    assert cast_updated.data["cast"] == str(actor2.pk)
    assert actor3.history.count() == 5
    episode_update_notif, special_added = actor3.history.all()[:2]
    assert episode_update_notif.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == ""


@mark.django_db
def test_removing_from_many_to_many_relations_not_recorded_for_unaffected_objects(
    episode, actors
):
    # arrange
    actor2, actor3 = actors
    episode.cast.add(actor3, actor2)
    episode.cast.remove(actor3)
    # assert
    assert episode.history.count() == 3
    assert actor3.history.count() == 5
    assert actor2.history.count() == 4
    ep_notif_1, ep_notif_2, special_added = actor2.history.all()[:3]
    assert ep_notif_1.related_field_history is not None
    assert ep_notif_2.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == str(episode.pk)


@mark.django_db
def test_clearing_many_to_many_relations_recorded_on_both_sides(episode, actors):
    # arrange
    actor2, actor3 = actors
    episode.cast.add(actor2, actor3)
    episode.cast.clear()
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == "~"
    assert cast_updated.history_diff == ["cast"]
    assert cast_updated.data["cast"] == ""
    assert actor2.history.count() == 5
    episode_update_notif, special_added = actor2.history.all()[:2]
    assert episode_update_notif.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == ""
    assert actor3.history.count() == 5
    episode_update_notif, special_added = actor3.history.all()[:2]
    assert episode_update_notif.related_field_history is not None
    assert special_added.history_type == "~"
    assert special_added.history_diff == ["filmography"]
    assert special_added.data["filmography"] == ""


@mark.django_db
def test_excluded_many_to_many_field_not_recorded_in_history(episode):
    # arrange
    coauthor = WriterFactory.create()
    episode.co_authors.add(coauthor)
    episode.co_authors.remove(coauthor)
    # assert
    coauthor_removed, coauthor_added = episode.history.all()[:2]
    assert coauthor_added.history_type == "~"
    assert coauthor_added.history_diff == ["co_authors"]
    assert coauthor_added.data["co_authors"] == str(coauthor.pk)
    assert coauthor_removed.history_type == "~"
    assert coauthor_removed.history_diff == ["co_authors"]
    assert coauthor_removed.data["co_authors"] == ""
    assert coauthor.history.count() == 1
    assert "contributions" not in coauthor.history.first().data


@mark.django_db
def test_history_generated_for_object_referenced_through_m2m_field_by_an_unregistered_object(  # noqa: E501
    choice, groups
):
    # arrange
    # Voter is not tracked in history but Group is so the group instances
    # should have history.
    voter = VoterFactory.create(choice=choice)
    group1, group2, group3 = groups
    # act
    voter.groups.set([group1, group2])
    voter.groups.add(group3)
    voter.groups.remove(group2)
    voter.groups.clear()
    # assert
    assert len(HistoryLogging._cleared_related_objects) == 0
    group1_cleared, group1_set = group1.history.all()[:2]
    assert group1_set.history_type == "~"
    assert group1_set.history_diff == ["voters"]
    assert group1_set.data["voters"] == str(voter.pk)
    assert group1_cleared.history_type == "~"
    assert group1_cleared.history_diff == ["voters"]
    assert group1_cleared.data["voters"] == ""
    group2_removed, group2_added = group2.history.all()[:2]
    assert group2_added.history_type == "~"
    assert group2_added.history_diff == ["voters"]
    assert group2_added.data["voters"] == str(voter.pk)
    assert group2_removed.history_type == "~"
    assert group2_removed.history_diff == ["voters"]
    assert group2_removed.data["voters"] == ""
    group3_cleared, group3_set = group3.history.all()[:2]
    assert group3_set.history_type == "~"
    assert group3_set.history_diff == ["voters"]
    assert group3_set.data["voters"] == str(voter.pk)
    assert group3_cleared.history_type == "~"
    assert group3_cleared.history_diff == ["voters"]
    assert group3_cleared.data["voters"] == ""


@mark.django_db
def test_history_generated_for_object_through_reverse_m2m_relation_with_untracked_added_objects(  # noqa: E501
    choice, group
):
    # arrange
    # Adding objects through the reverse many-to-many relation: Voters to a
    # Group. The voters will not have history but the group will.
    voter1, voter2, voter3 = VoterFactory.create_batch(size=3, choice=choice)
    # act
    group.voters.set([voter1, voter2])
    group.voters.add(voter3)
    group.voters.remove(voter2)
    group.voters.clear()
    # assert
    assert len(HistoryLogging._cleared_related_objects) == 0
    (
        voters_cleared,
        voter2_removed,
        voter3_added,
        voters_set,
        group_created,
    ) = group.history.all()
    assert voters_cleared.history_type == "~"
    assert voters_cleared.history_diff == ["voters"]
    assert voters_cleared.data["voters"] == ""
    assert voter2_removed.history_type == "~"
    assert voter2_removed.history_diff == ["voters"]
    assert voter2_removed.data["voters"] == history_format_fks([voter1.pk, voter3.pk])
    assert voter3_added.history_type == "~"
    assert voter3_added.history_diff == ["voters"]
    assert voter3_added.data["voters"] == history_format_fks(
        [voter1.pk, voter2.pk, voter3.pk]
    )
    assert voters_set.history_type == "~"
    assert voters_set.history_diff == ["voters"]
    assert voters_set.data["voters"] == history_format_fks([voter1.pk, voter2.pk])
    assert group_created.history_type == "+"


@mark.django_db
def test_history_generated_for_object_with_m2m_field_to_untracked_object(
    group,
):
    # arrange
    # Group is tracked by history but Admin is not. History will be generated
    # only for Group.
    admin1, admin2, admin3 = AdminFactory.create_batch(size=3)
    # act
    group.admins.set([admin1, admin2])
    group.admins.add(admin3)
    group.admins.remove(admin2)
    group.admins.clear()
    # assert
    assert len(HistoryLogging._cleared_related_objects) == 0
    (
        admins_cleared,
        admin2_removed,
        admin3_added,
        admins_set,
        group_created,
    ) = group.history.all()
    assert admins_cleared.history_type == "~"
    assert admins_cleared.history_diff == ["admins"]
    assert admins_cleared.data["admins"] == ""
    assert admin2_removed.history_type == "~"
    assert admin2_removed.history_diff == ["admins"]
    assert admin2_removed.data["admins"] == history_format_fks([admin1.pk, admin3.pk])
    assert admin3_added.history_type == "~"
    assert admin3_added.history_diff == ["admins"]
    assert admin3_added.data["admins"] == history_format_fks(
        [admin1.pk, admin2.pk, admin3.pk]
    )
    assert admins_set.history_type == "~"
    assert admins_set.history_diff == ["admins"]
    assert admins_set.data["admins"] == history_format_fks([admin1.pk, admin2.pk])
    assert group_created.history_type == "+"


@mark.django_db
def test_history_generated_for_objects_added_through_reverse_m2m_relation_on_an_untracked_object(  # noqa: E501
    groups,
):
    # arrange
    # Adding objects through the reverse many-to-many relation: Voters to a
    # Group. The voters will not have history but the group will.
    admin = AdminFactory.create()
    group1, group2, group3 = groups
    # act
    admin.groups.set([group1, group2])
    admin.groups.add(group3)
    admin.groups.remove(group2)
    admin.groups.clear()
    # assert
    assert len(HistoryLogging._cleared_related_objects) == 0
    group1_cleared, group1_set = group1.history.all()[:2]
    assert group1_set.history_type == "~"
    assert group1_set.history_diff == ["admins"]
    assert group1_set.data["admins"] == str(admin.pk)
    assert group1_cleared.history_type == "~"
    assert group1_cleared.history_diff == ["admins"]
    assert group1_cleared.data["admins"] == ""
    group2_removed, group2_added = group2.history.all()[:2]
    assert group2_added.history_type == "~"
    assert group2_added.history_diff == ["admins"]
    assert group2_added.data["admins"] == str(admin.pk)
    assert group2_removed.history_type == "~"
    assert group2_removed.history_diff == ["admins"]
    assert group2_removed.data["admins"] == ""
    group3_cleared, group3_set = group3.history.all()[:2]
    assert group3_set.history_type == "~"
    assert group3_set.history_diff == ["admins"]
    assert group3_set.data["admins"] == str(admin.pk)
    assert group3_cleared.history_type == "~"
    assert group3_cleared.history_diff == ["admins"]
    assert group3_cleared.data["admins"] == ""


@mark.django_db
def test_additional_data_from_initially_changed_instance_copied_to_history_of_fk_field(
    show,
):
    # act
    SeasonFactory.create(
        show=show,
        additional_data={
            "where_from": "Console",
            "smth": "Abc",
        },
    )
    # assert
    show_updated_with_season = show.history.first()
    assert show_updated_with_season.history_type == "~"
    assert show_updated_with_season.history_diff == ["season"]
    expected = {"where_from": "Console", "smth": "Abc"}
    assert show_updated_with_season.additional_data == expected


@mark.django_db
def test_additional_data_from_initially_changed_instance_copied_to_history_of_1_to_1_field(  # noqa: E501
    writer, show
):
    # act
    episode = EpisodeFactory.create(
        show=show,
        author=writer,
        additional_data={
            "where_from": "API",
            "smth": "Some new information",
        },
    )
    # assert
    writer_update_with_work = writer.history.get(
        history_type="~",
        history_diff__contains=["work"],
        data__work=str(episode.pk),
    )
    expected = {"where_from": "API", "smth": "Some new information"}
    assert writer_update_with_work.additional_data == expected


@mark.django_db
def test_additional_data_from_initially_changed_instance_copied_to_history_of_many_to_many_field(  # noqa: E501
    episode2, group
):
    # arrange
    episode2.additional_data = {
        "where_from": "Space",
        "message": "We come in peace!",
    }
    # act
    episode2.groups.add(group)
    # assert
    group_update_with_episode = group.history.get(
        history_type="~",
        history_diff__contains=["episodes"],
        data__episodes=str(episode2.pk),
    )
    expected = {"where_from": "Space", "message": "We come in peace!"}
    assert group_update_with_episode.additional_data == expected


@mark.django_db
def test_reordering_many_to_many_does_not_generate_record(episode, actors):
    actor2, actor3 = actors
    episode.cast.add(actor3, actor2)
    cast_updated = episode.history.first()
    # re-order m2m
    cast_updated.data["cast"] = f"{actor3.id}, {actor2.id}"
    cast_updated.save()
    episode.save()

    assert episode.history.count() == 2  # save + 1 update
