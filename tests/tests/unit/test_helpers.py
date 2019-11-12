from atris.models.helpers import diff_is_fake


def test_diff_is_fake():
    data = {'key': '123, 456'}
    prev_data = {'key': '456, 123'}
    diff_fields = {'key'}

    assert diff_is_fake(data, prev_data, diff_fields)


def test_diff_is_fake_new_key():
    data = {'key': '123, 456'}
    prev_data = {}
    diff_fields = {'key'}

    assert not diff_is_fake(data, prev_data, diff_fields)


def test_diff_is_fake_bad_key():
    data = {'key': '123, 456'}
    prev_data = {}
    diff_fields = {'bad-key'}

    assert not diff_is_fake(data, prev_data, diff_fields)


def test_diff_is_fake_none():
    data = {'key': None}
    prev_data = {'key': '123, 345'}
    diff_fields = {'key'}

    assert not diff_is_fake(data, prev_data, diff_fields)
