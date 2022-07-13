from pytest import fixture

from tests.factories import (
    ActorFactory,
    ChoiceFactory,
    Episode2Factory,
    EpisodeFactory,
    GroupFactory,
    LinkFactory,
    PollFactory,
    SeasonFactory,
    ShowFactory,
    SpecialFactory,
    VoterFactory,
    WriterFactory,
)


@fixture(scope="function")
def actor():
    return ActorFactory.create()


@fixture(scope="function")
def poll():
    return PollFactory.create()


@fixture(scope="function")
def choice(poll):
    return ChoiceFactory.create(poll=poll)


@fixture(scope="function")
def voter(choice):
    return VoterFactory.create(choice=choice)


@fixture(scope="function")
def show():
    return ShowFactory.create()


@fixture(scope="function")
def writer():
    return WriterFactory.create()


@fixture(scope="function")
def episode(show, writer):
    return EpisodeFactory.create(show=show, author=writer)


@fixture(scope="function")
def episode2(show, writer):
    return Episode2Factory.create(show=show, author=writer)


@fixture(scope="function")
def season(show):
    return SeasonFactory.create(show=show)


@fixture(scope="function")
def special(show, writer):
    return SpecialFactory.create(show=show, author=writer)


@fixture(scope="function")
def link():
    return LinkFactory.create()


@fixture(scope="function")
def actors():
    return ActorFactory.create_batch(size=2)


@fixture(scope="function")
def group():
    return GroupFactory.create()


@fixture(scope="function")
def groups():
    return GroupFactory.create_batch(size=3)


def history_format_fks(ids):
    """
    Sorts a list of ids and converts to the format compatible with
    atris data
    :param ids: list of primary keys
    :return: string of concatenated ids after sort
    """
    sorted_ids = [str(u) for u in sorted(ids)]
    return ", ".join(sorted_ids)
