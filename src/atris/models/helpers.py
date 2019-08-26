import re

from django.core.exceptions import ObjectDoesNotExist
from django.db import router


def get_diff_fields(model, data, previous_data, excluded_fields_names,
                    check_fake=True):
    """
    Returns the fields of `data` for which the values differ in
    `previous_data`. The fields that are given in `excluded_fields_names` are
    not registered as having changed.
    :param model: - the Django model or an instance of that model.
    """
    if not previous_data:
        return []
    diff_fields = [
        model._meta.get_field(f).name for f, v in data.items()
        if f not in excluded_fields_names and previous_data.get(f) != v
    ]
    if check_fake and diff_is_fake(data, previous_data, diff_fields):
        # Takes into account that in atris < 1.4
        # m2m relation ids were unordered,
        # which often yielded false positives
        return []
    return diff_fields


def diff_is_fake(data, prev_data, diff_fields):
    """
    If all the diff_fields have values like '123, 456' vs '456, 123'
    it means it's a false diff.
    """
    for field_name in diff_fields:
        value = data[field_name]
        id_list = re.match(r'^(\d+,\s)+\d+$', value)
        if not id_list:
            return False
        else:
            old_set = set(prev_data[field_name].split(', '))
            curr_set = set(data[field_name].split(', '))
            if old_set != curr_set:
                return False
    return True


def get_instance_field_data(instance):
    """
    Returns a dictionary with the attribute values of instance, serialized as
    strings.
    """
    data = {}
    instance_meta = instance._meta
    for field in instance_meta.get_fields():
        name = field.name
        if name in instance_meta.history_logging.excluded_fields_names:
            continue
        attname = get_attribute_name_from_field(field)
        try:
            value = getattr(instance, attname)
        except ObjectDoesNotExist:
            value = None
        if field.many_to_many or field.one_to_many:
            ids = from_writable_db(value).values_list('pk', flat=True)
            data[name] = ', '.join([str(e) for e in ids.order_by('pk')])
        elif field.one_to_one and not field.concrete:
            data[name] = str(value.pk) if value is not None else None
        else:
            data[name] = str(value) if value is not None else None
    return data


def get_attribute_name_from_field(field, flat_fk=True):
    accessor_for_simple_fields = 'attname' if flat_fk else 'name'
    if hasattr(field, 'fk_field'):  # generic foreign key
        attname = field.fk_field
    elif hasattr(field, 'get_accessor_name'):  # many-to-* relation field
        attname = field.get_accessor_name()
    elif hasattr(field, accessor_for_simple_fields):
        # regular field or foreign key
        attname = getattr(field, accessor_for_simple_fields)
    else:
        raise TypeError("Can't determine accessor for field {}".format(field))
    return attname


def from_writable_db(manager):
    """
    When using a DB router in which the reads are done through a different
    connection than the writes, the data may differ, resulting in incorrect
    history logging. Use the writable DB whenever it is essential to get the
    latest data.
    """
    writable_db = router.db_for_write(manager.model)
    return manager.using(writable_db)
