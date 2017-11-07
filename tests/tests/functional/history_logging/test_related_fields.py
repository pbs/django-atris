from pytest import mark

from tests.models import Show, Actor, Writer, Link


# TODO: Add tests for Issue#15


@mark.django_db
def test_related_object_recorded_with_the_specified_related_name(show):
    # assert
    assert 'specials' in show.history.first().data


@mark.django_db
def test_related_object_recorded_with_module_name_if_no_related_name_specified(
        show):
    # assert
    assert 'season' in show.history.first().data


@mark.skip(reason='Issue#18')
@mark.django_db
def test_changes_to_many_to_one_relations_recorded_automatically(
        show, episode, season):
    # arrange
    # assert
    season_added, special_added = show.history.all()[:2]
    assert season_added.history_type == '~'
    assert season_added.history_diff == ['season']
    assert season_added.data['season'] == str(season.pk)
    assert special_added.history_type == '~'
    assert special_added.history_diff == ['specials']
    assert special_added.data['specials'] == str(episode.pk)


@mark.skip(reason='Issue#18')
@mark.django_db
def test_changing_a_foreign_key_value_reflected_on_both_past_and_present_referenced_objects(  # noqa
        show, season):
    # arrange
    show2 = Show.objects.create(title='Mercy Street', description='')
    # act
    season.show = show2
    season.save()
    # assert
    season_added = show2.history.first()
    assert season_added.history_type == '~'
    assert season_added.history_diff == ['season']
    assert season_added.data['season'] == str(season.pk)
    season_removed = show.history.first()
    assert season_removed.history_type == '~'
    assert season_removed.history_diff == ['season']
    assert season_removed.data['season'] == ''


@mark.django_db
def test_generic_foreign_keys_backed_by_a_generic_relation_are_recorded(show):
    # arrange
    show_url_1 = Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street',
        related_object=show
    )
    show_url_2 = Link.objects.create(
        name='Amazon link',
        url='http://amazon.com/mercy-street',
        related_object=show
    )
    # assert
    link_added = show.history.first()
    assert link_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert link_added.history_diff == ['links']
    expected_links = '{}, {}'.format(show_url_2.pk, show_url_1.pk)
    assert link_added.data['links'] == expected_links


@mark.django_db
def test_generic_foreign_keys_not_backed_by_a_generic_relation_are_not_recorded(  # noqa
        episode):
    # arrange
    Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street-ep1',
        related_object=episode
    )
    # assert
    special_history = episode.history.first()
    expected_keys = {'id', 'title', 'description', 'show', 'season', 'cast',
                     'author', 'co_authors'}  # no relation to Link
    assert set(special_history.data.keys()) == expected_keys


@mark.django_db
def test_one_to_one_relations_tracked_on_both_models(writer, episode):
    # assert
    special_added_for_writer = writer.history.first()
    assert special_added_for_writer.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added_for_writer.history_diff == ['work']
    assert special_added_for_writer.data['work'] == str(episode.pk)
    special_created = episode.history.first()
    assert special_created.history_type == '+'
    assert special_created.data['author'] == str(writer.pk)


@mark.django_db
def test_adding_to_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    # assert
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == '{}, {}'.format(actor1.pk, actor2.pk)
    special_added = actor1.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)


@mark.django_db
def test_removing_from_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    episode.cast.remove(actor1)
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == str(actor2.pk)
    assert actor1.history.count() == 3
    special_added = actor1.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == ''


@mark.django_db
def test_removing_from_many_to_many_relations_not_recorded_for_unaffected_objects(  # noqa
        episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    episode.cast.remove(actor1)
    # assert
    assert episode.history.count() == 3
    assert actor1.history.count() == 3
    assert actor2.history.count() == 3
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)


@mark.django_db
def test_clearing_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor1 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor1, actor2)
    episode.cast.clear()
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == ''
    assert actor1.history.count() == 3
    special_added = actor1.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == ''
    assert actor2.history.count() == 3
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#18 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == ''


@mark.django_db
def test_excluded_many_to_many_field_not_recorded_in_history(episode):
    # arrange
    coauthor = Writer.objects.create(name='Walon Green')
    episode.co_authors.add(coauthor)
    episode.co_authors.remove(coauthor)
    # assert
    coauthor_removed, coauthor_added = episode.history.all()[:2]
    assert coauthor_added.history_type == '~'
    assert coauthor_added.history_diff == ['co_authors']
    assert coauthor_added.data['co_authors'] == str(coauthor.pk)
    assert coauthor_removed.history_type == '~'
    assert coauthor_removed.history_diff == ['co_authors']
    assert coauthor_removed.data['co_authors'] == ''
    assert coauthor.history.count() == 1
    assert 'contributions' not in coauthor.history.first().data
