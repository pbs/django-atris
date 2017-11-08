from pytest import mark

from tests.models import Show, Actor, Writer, Link, Voter, Group, Admin


@mark.django_db
def test_related_object_recorded_with_the_specified_related_name(show):
    # assert
    assert 'specials' in show.history.first().data


@mark.django_db
def test_related_object_recorded_with_module_name_if_no_related_name_specified(
        show):
    # assert
    assert 'season' in show.history.first().data


@mark.skip(reason='Issue#38')
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


@mark.skip(reason='Issue#38')
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
    show_url_3 = Link.objects.create(
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
    # TODO: uncomment after Issue#38 is fixed
    # assert link_added.history_diff == ['links']
    expected_links = '{}, {}'.format(show_url_2.pk, show_url_3.pk)
    assert link_added.data['links'] == expected_links


@mark.django_db
def test_generic_foreign_keys_not_backed_by_a_generic_relation_are_not_recorded(  # noqa
        episode):
    # arrange
    Link.objects.create(
        name='PBS link',
        url='http://pbs.org/mercy-street-ep3',
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
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added_for_writer.history_diff == ['work']
    assert special_added_for_writer.data['work'] == str(episode.pk)
    special_created = episode.history.first()
    assert special_created.history_type == '+'
    assert special_created.data['author'] == str(writer.pk)


@mark.django_db
def test_adding_to_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor3 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor3, actor2)
    # assert
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == '{}, {}'.format(actor3.pk, actor2.pk)
    special_added = actor3.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)


@mark.django_db
def test_removing_from_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor3 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor3, actor2)
    episode.cast.remove(actor3)
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == str(actor2.pk)
    assert actor3.history.count() == 3
    special_added = actor3.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == ''


@mark.django_db
def test_removing_from_many_to_many_relations_not_recorded_for_unaffected_objects(  # noqa
        episode):
    # arrange
    actor3 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor3, actor2)
    episode.cast.remove(actor3)
    # assert
    assert episode.history.count() == 3
    assert actor3.history.count() == 3
    assert actor2.history.count() == 3
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == str(episode.pk)


@mark.django_db
def test_clearing_many_to_many_relations_recorded_on_both_sides(episode):
    # arrange
    actor3 = Actor.objects.create(name='McKinley Belcher III')
    actor2 = Actor.objects.create(name='Suzanne Bertish')
    episode.cast.add(actor3, actor2)
    episode.cast.clear()
    # assert
    assert episode.history.count() == 3
    cast_updated = episode.history.first()
    assert cast_updated.history_type == '~'
    assert cast_updated.history_diff == ['cast']
    assert cast_updated.data['cast'] == ''
    assert actor3.history.count() == 3
    special_added = actor3.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
    # assert special_added.history_diff == ['filmography']
    assert special_added.data['filmography'] == ''
    assert actor2.history.count() == 3
    special_added = actor2.history.first()
    assert special_added.history_type == '~'
    # TODO: uncomment after Issue#38 is fixed
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


@mark.skip(reason='Issue#15')
@mark.django_db
def test_history_generated_for_object_referenced_through_m2m_field_by_an_unregistered_object(  # noqa
        choice):
    # arrange
    # Voter is not tracked in history but Group is so the group instances
    # should have history.
    voter = Voter.objects.create(choice=choice, name='Joe')
    group1 = Group.objects.create(name='Group1')
    group2 = Group.objects.create(name='Group2')
    group3 = Group.objects.create(name='Group3')
    # act
    voter.groups.set([group1, group2])
    voter.groups.add(group3)
    voter.groups.remove(group2)
    voter.groups.clear()
    # assert
    group1_set, group1_cleared = group1.history.all()[1:]
    assert group1_set.history_type == '~'
    assert group1_set.history_diff == ['voters']
    assert group1_set.data['voters'] == str(voter.pk)
    assert group1_cleared.history_type == '~'
    assert group1_cleared.history_diff == ['voters']
    assert group1_cleared.data['voters'] == ''
    group2_added, group2_removed = group2.history.all()[1:]
    assert group2_added.history_type == '~'
    assert group2_added.history_diff == ['voters']
    assert group2_added.data['voters'] == str(voter.pk)
    assert group2_removed.history_type == '~'
    assert group2_removed.history_diff == ['voters']
    assert group2_removed.data['voters'] == ''
    group3_set, group3_cleared = group3.history.all()[1:]
    assert group3_set.history_type == '~'
    assert group3_set.history_diff == ['voters']
    assert group3_set.data['voters'] == str(voter.pk)
    assert group3_cleared.history_type == '~'
    assert group3_cleared.history_diff == ['voters']
    assert group3_cleared.data['voters'] == ''


@mark.django_db
def test_history_generated_for_object_through_reverse_m2m_relation_with_untracked_added_objects(  # noqa
        choice):
    # arrange
    # Adding objects through the reverse many-to-many relation: Voters to a
    # Group. The voters will not have history but the group will.
    group = Group.objects.create(name='GroupX')
    voter1 = Voter.objects.create(choice=choice, name='Joe')
    voter2 = Voter.objects.create(choice=choice, name='Mary')
    voter3 = Voter.objects.create(choice=choice, name='Robin')
    # act
    group.voters.set([voter1, voter2])
    group.voters.add(voter3)
    group.voters.remove(voter2)
    group.voters.clear()
    # assert
    (voters_cleared,
     voter2_removed,
     voter3_added,
     voters_set,
     group_created) = group.history.all()
    assert voters_cleared.history_type == '~'
    assert voters_cleared.history_diff == ['voters']
    assert voters_cleared.data['voters'] == ''
    assert voter2_removed.history_type == '~'
    assert voter2_removed.history_diff == ['voters']
    assert voter2_removed.data['voters'] == '{}, {}'.format(voter1.pk,
                                                            voter3.pk)
    assert voter3_added.history_type == '~'
    assert voter3_added.history_diff == ['voters']
    assert voter3_added.data['voters'] == '{}, {}, {}'.format(
        voter1.pk, voter2.pk, voter3.pk)
    assert voters_set.history_type == '~'
    assert voters_set.history_diff == ['voters']
    assert voters_set.data['voters'] == '{}, {}'.format(voter1.pk, voter2.pk)
    assert group_created.history_type == '+'


@mark.django_db
def test_history_generated_for_object_with_m2m_field_to_untracked_object():  # noqa
    # arrange
    # Group is tracked by history but Admin is not. History will be generated
    # only for Group.
    group = Group.objects.create(name='GroupX')
    admin1 = Admin.objects.create(name='Joe')
    admin2 = Admin.objects.create(name='Mary')
    admin3 = Admin.objects.create(name='Robin')
    # act
    group.admins.set([admin1, admin2])
    group.admins.add(admin3)
    group.admins.remove(admin2)
    group.admins.clear()
    # assert
    (admins_cleared,
     admin2_removed,
     admin3_added,
     admins_set,
     group_created) = group.history.all()
    assert admins_cleared.history_type == '~'
    assert admins_cleared.history_diff == ['admins']
    assert admins_cleared.data['admins'] == ''
    assert admin2_removed.history_type == '~'
    assert admin2_removed.history_diff == ['admins']
    assert admin2_removed.data['admins'] == '{}, {}'.format(admin1.pk,
                                                            admin3.pk)
    assert admin3_added.history_type == '~'
    assert admin3_added.history_diff == ['admins']
    assert admin3_added.data['admins'] == '{}, {}, {}'.format(
        admin1.pk, admin2.pk, admin3.pk)
    assert admins_set.history_type == '~'
    assert admins_set.history_diff == ['admins']
    assert admins_set.data['admins'] == '{}, {}'.format(admin1.pk, admin2.pk)
    assert group_created.history_type == '+'


@mark.skip(reason='Issue#15')
@mark.django_db
def test_history_generated_for_objects_added_through_reverse_m2m_relation_on_an_untracked_object():  # noqa
    # arrange
    # Adding objects through the reverse many-to-many relation: Voters to a
    # Group. The voters will not have history but the group will.
    admin = Admin.objects.create(name='Joe')
    group1 = Group.objects.create(name='Group1')
    group2 = Group.objects.create(name='Group2')
    group3 = Group.objects.create(name='Group3')
    # act
    admin.groups.set([group1, group2])
    admin.groups.add(group3)
    admin.groups.remove(group2)
    admin.groups.clear()
    # assert
    group1_set, group1_cleared = group1.history.all()[1:]
    assert group1_set.history_type == '~'
    assert group1_set.history_diff == ['admins']
    assert group1_set.data['admins'] == str(admin.pk)
    assert group1_cleared.history_type == '~'
    assert group1_cleared.history_diff == ['admins']
    assert group1_cleared.data['admins'] == ''
    group2_added, group2_removed = group2.history.all()[1:]
    assert group2_added.history_type == '~'
    assert group2_added.history_diff == ['admins']
    assert group2_added.data['admins'] == str(admin.pk)
    assert group2_removed.history_type == '~'
    assert group2_removed.history_diff == ['admins']
    assert group2_removed.data['admins'] == ''
    group3_set, group3_cleared = group3.history.all()[1:]
    assert group3_set.history_type == '~'
    assert group3_set.history_diff == ['admins']
    assert group3_set.data['admins'] == str(admin.pk)
    assert group3_cleared.history_type == '~'
    assert group3_cleared.history_diff == ['admins']
    assert group3_cleared.data['admins'] == ''
