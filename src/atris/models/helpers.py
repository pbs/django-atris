from django.core.exceptions import ObjectDoesNotExist


def get_diff_fields(model, data, previous_data, excluded_fields_names):
    """
    Returns the fields of `data` for which the values differ in
    `previous_data`. The fields that are given in `excluded_fields_names` are
    not registered as having changed.
    :param model: - the Django model or an instance of that model.
    """
    if not previous_data:
        return None
    result = [model._meta.get_field(f).name
              for f, v in data.items()
              if f not in excluded_fields_names and previous_data.get(f) != v]
    return result


def get_model_field_data(model):
    data = {}
    model_meta = model._meta
    for field in model_meta.get_fields():
        name = field.name
        if name in model_meta.history_logging.excluded_fields_names:
            continue
        attname = (field.attname if hasattr(field, 'attname')
                   else field.get_accessor_name())
        try:
            value = getattr(model, attname)
        except ObjectDoesNotExist:
            value = None
        if field.many_to_many or field.one_to_many:
            data[name] = ', '.join([str(e.pk) for e in value.all()])
        else:
            data[name] = str(value) if value is not None else None
    return data
