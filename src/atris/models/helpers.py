import ast
import json
import re

from typing import Dict, List, Optional, Type, Union

from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ObjectDoesNotExist
from django.db import router
from django.db.models import Model


def get_diff_fields(
    model: Union[Model, Type[Model]],
    data: Dict,
    previous_data: Dict,
    excluded_fields_names: List[str],
) -> Optional[List[str]]:
    """

    Args:
        model: the Django model or an instance of that model
        data: current instance data as dictionary
        previous_data: previous instance data as dictionary
        excluded_fields_names: excluded fields names of the specified model

    Returns: the fields of `data` for which the values differ in

    """
    if not previous_data:
        return None
    diff_fields = []
    for f, v in data.items():
        if f in excluded_fields_names:
            continue
        model_field = model._meta.get_field(f)
        try:
            previous_value = previous_data[f]
        except KeyError:
            if v != get_default_value(model_field):
                diff_fields.append(model_field.name)
        else:
            is_field_different = is_different(
                old=previous_value,
                new=v,
                field=model_field,
            )
            if is_field_different:
                diff_fields.append(model_field.name)
    return diff_fields


def get_default_value(field):
    try:
        default_value = field.get_default()
        return str(default_value) if default_value is not None else None
    except AttributeError as e:
        error_message = str(e)
        if "ManyTo" in error_message:
            # ManyToManyRel or ManyToOneRel
            return ""
        return None


def get_field_internal_type(field):
    try:
        return field.get_internal_type().strip()
    except AttributeError as e:
        if type(field) == GenericForeignKey:
            return "GenericForeignKey"
        else:
            raise e


def is_different(old, new, field):
    # serializing/deserializing a json object can change key order
    id_list = re.compile(r"^(\d+,\s)+\d+$")
    new_list = re.match(id_list, new or "")
    prev_list = re.match(id_list, old or "")
    is_list = new_list and prev_list
    is_relation_to_many = (field.one_to_many or field.many_to_many) and is_list

    field_internal_type = get_field_internal_type(field=field)
    # django jsonfield allows both python dicts or raw json
    if field_internal_type == "JSONField":
        try:
            # for valid python dict
            old = ast.literal_eval(old) if old else old
        except ValueError:
            # for string of json
            old = json.loads(old) if old else old
        try:
            new = ast.literal_eval(new) if new else new
        except ValueError:
            new = json.loads(new) if new else new
    elif is_relation_to_many or field_internal_type == "ArrayField":
        old = set(old.split(", ")) if old else old
        new = set(new.split(", ")) if new else new
    return old != new


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
            ids = from_writable_db(value).values_list("pk", flat=True)
            data[name] = ", ".join([str(e) for e in ids.order_by("pk")])
        elif field.one_to_one and not field.concrete:
            data[name] = str(value.pk) if value is not None else None
        else:
            data[name] = str(value) if value is not None else None
    return data


def get_attribute_name_from_field(field, flat_fk=True):
    accessor_for_simple_fields = "attname" if flat_fk else "name"
    if hasattr(field, "fk_field"):  # generic foreign key
        attname = field.fk_field
    elif hasattr(field, "get_accessor_name"):  # many-to-* relation field
        attname = field.get_accessor_name()
    elif hasattr(field, accessor_for_simple_fields):
        # regular field or foreign key
        attname = getattr(field, accessor_for_simple_fields)
    else:
        raise TypeError(f"Can't determine accessor for field {field}")
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
