
def get_diff_fields(model, data, previous_data, excluded_fields_names):
    """
    Returns the fields of `data` for which the values differ in
    `previous_data`. The fields that are given in `excluded_fields_names` are
    not registered as having changed.
    :param model: - the Django model or an instance of that model.
    """
    if not previous_data:
        return None
    result = [model._meta.get_field(f).verbose_name
              for f, v in data.items()
              if f not in excluded_fields_names and previous_data.get(f) != v]
    return result
