import logging
import threading

from copy import copy
from sys import modules

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_delete, post_save

from .exceptions import InvalidRelatedField
from .helpers import from_writable_db, get_diff_fields, get_instance_field_data
from .historical_record import get_history_model


registered_models = {}
logger = logging.getLogger(__name__)
HistoricalRecord = get_history_model()


def fake_save(obj, created=False):
    """
    Trigger the signal that will generate History for the given object.
    Useful when a change on an untracked object does not generate history on a
    related tracked object or when using bulk_create, which does not trigger
    the pre/post_save signals by default.
    """
    obj._meta.history_logging.post_save(obj, created=created)


class HistoryManager:
    def __get__(self, instance, model):
        if instance and model:
            return HistoricalRecord.objects.by_model_and_model_id(
                model,
                instance.pk,
            )
        if model:
            return HistoricalRecord.objects.by_model(model)


# noinspection PyProtectedMember,PyAttributeOutsideInit
class HistoryLogging:

    thread = threading.local()
    _cleared_related_objects = dict()

    def __init__(
        self,
        additional_data_param_name="",
        excluded_fields_param_name="",
        ignore_history_for_users="",
        interested_related_fields="",
        history_user_param_name="",
    ):
        """
        :param additional_data_param_name: String used to determine which field
         on the object contains a dict holding any additional data.
        :type additional_data_param_name: str

        :param excluded_fields_param_name: String used to determine which field
            on the object contains a list holding the names of the fields which
            should not be tracked in the history.
        :param ignore_history_for_users: String used to determine which field
            on the object contains a dictionary holding the names of the users
            for which history should not be tracked.
            Dict should contain

        :type excluded_fields_param_name: str
        """
        self.additional_data_param_name = additional_data_param_name
        self.class_additional_data_name = "__" + additional_data_param_name
        self.excluded_fields_param_name = excluded_fields_param_name
        self.interested_related_fields_param_name = interested_related_fields
        self.ignore_history_for_users_param_name = ignore_history_for_users
        self.history_user_param_name = history_user_param_name

    def contribute_to_class(self, cls, name):
        if cls not in registered_models:
            registered_models[cls] = {
                "additional_data_param_name": self.class_additional_data_name,
                "excluded_fields_param_name": self.excluded_fields_param_name,
            }
        setattr(cls._meta, "history_logging", self)
        setattr(cls, name, HistoryManager())
        self.module = cls.__module__
        self.model = cls

    def set_additional_data_properties(self, cls):
        if self.additional_data_param_name:
            additional_data_value = getattr(
                cls,
                self.additional_data_param_name,
                dict(),
            )
            class_name = cls.__name__
            setattr(
                cls,
                self.class_additional_data_name,
                additional_data_value,
            )
            logger.debug(
                "Set class attribute {}.{}".format(
                    class_name,
                    self.class_additional_data_name,
                ),
            )
            default_data_param_name = "default_" + self.additional_data_param_name
            setattr(
                cls,
                default_data_param_name,
                self.default_additional_data_property_maker(),
            )
            logger.debug(
                "Set property {}.{}".format(
                    class_name,
                    default_data_param_name,
                ),
            )
            setattr(
                cls,
                self.additional_data_param_name,
                self.additional_data_property_maker(),
            )
            logger.debug(
                "Set property {}.{}".format(
                    class_name,
                    self.additional_data_param_name,
                ),
            )

    def default_additional_data_property_maker(self):
        def getter(instance):
            return getattr(instance, self.class_additional_data_name)

        return property(fget=getter)

    def additional_data_property_maker(self):
        property_name = "_" + self.additional_data_param_name

        def getter(instance):
            if not hasattr(instance, property_name):
                logger.debug(
                    "{} not defined on {}. Getting class default from "
                    "property: {}".format(
                        property_name,
                        instance.__class__.__name__,
                        self.class_additional_data_name,
                    ),
                )
                default = getattr(instance, self.class_additional_data_name)
                setattr(instance, property_name, copy(default))
            return getattr(instance, property_name)

        def setter(instance, value):
            setattr(instance, property_name, value)

        return property(fget=getter, fset=setter)

    def set_excluded_fields_names(self, cls):
        self.excluded_fields_names = getattr(
            cls,
            self.excluded_fields_param_name,
            [],
        )

    def set_interested_related_fields(self, cls):
        self.interested_related_fields = set(
            getattr(
                cls,
                self.interested_related_fields_param_name,
                [],
            ),
        )
        for field_name in self.interested_related_fields:
            field = cls._meta.get_field(field_name)
            if not field.is_relation:
                raise InvalidRelatedField(
                    "{} is not a related field on {}".format(
                        field.name,
                        cls,
                    ),
                )

    def register_signal_handlers(self, sender):
        post_save.connect(self.post_save, sender=sender, weak=False)
        post_delete.connect(self.post_delete, sender=sender, weak=False)
        get_m2m_through_classes = M2MThroughClassesGatherer(sender)
        through_classes = get_m2m_through_classes()
        for through_class in through_classes:
            m2m_changed.connect(
                self.m2m_changed,
                sender=through_class,
                weak=False,
            )

    def post_save(self, instance, created=True, raw=False, **kwargs):
        if not raw:
            self._create_historical_record(
                instance,
                created and HistoricalRecord.CREATE or HistoricalRecord.UPDATE,
            )

    def post_delete(self, instance, **kwargs):
        self._create_historical_record(instance, HistoricalRecord.DELETE)

    def m2m_changed(self, instance, action, reverse, model, pk_set, **kwargs):
        only_related_model_tracks_history = not hasattr(
            instance._meta, "history_logging"
        ) and hasattr(model._meta, "history_logging")
        if only_related_model_tracks_history:
            if action in ("post_add", "post_remove"):
                for related_object in model.objects.filter(pk__in=pk_set):
                    self._create_historical_record(
                        related_object,
                        HistoricalRecord.UPDATE,
                    )
            elif action == "pre_clear":
                field_name = find_m2m_field_name_by_model(
                    instance._meta,
                    model,
                    reverse,
                )
                related_objects = getattr(instance, field_name).all()
                self._cleared_related_objects[instance] = list(related_objects)
            elif action == "post_clear" and instance in self._cleared_related_objects:
                related_objects = self._cleared_related_objects.pop(instance)
                for related_object in related_objects:
                    self._create_historical_record(
                        related_object,
                        HistoricalRecord.UPDATE,
                        False,
                    )
        elif action.startswith("post"):
            self._create_historical_record(instance, HistoricalRecord.UPDATE)

    def _create_historical_record(
        self, instance, history_type, propagate_to_related_fields=True
    ):
        history_user = self.get_history_user(instance)
        history_user_id, history_user_name = get_history_user_id_and_name(
            history_user,
        )
        generate_history = HistoricalRecordGenerator(
            instance,
            history_type,
            history_user_id,
            history_user_name,
            self.get_ignored_users(instance),
            propagate_to_related_fields,
        )
        generate_history()

    def get_ignored_users(self, instance):
        return getattr(instance, self.ignore_history_for_users_param_name, {})

    def get_history_user(self, instance):
        """
        Get the modifying user from the middleware or the user registered on
        the modified instance under the attribute declared with the name
        specified by the `history_user_param_name` init variable.
        """
        try:
            if self.thread.request.user.is_authenticated:
                return self.thread.request.user
        except AttributeError:
            return getattr(instance, "history_user", None)


def get_history_user_id_and_name(user):
    if not user:
        return None, None
    full_name = (
        user.get_full_name()
        if callable(
            getattr(user, "get_full_name", None),
        )
        else None
    )
    username = (
        user.get_username()
        if callable(
            getattr(user, "get_username", None),
        )
        else None
    )
    if user:
        history_user = full_name or getattr(user, "email", None) or username
        return user.id, history_user
    return user.id, None


def find_m2m_field_name_by_model(in_model_meta, for_model, reverse_m2m):
    if reverse_m2m:
        fields = in_model_meta.related_objects
    else:
        fields = in_model_meta.many_to_many
    for field in fields:
        target_models = [for_model] + [p for p in for_model._meta.parents]
        if field.many_to_many and field.related_model in target_models:
            return field.name


class M2MThroughClassesGatherer:
    def __init__(self, cls):
        self.cls = cls

    def __call__(self):
        m2m_related_throughs = [
            self.get_through_class(ro.through)
            for ro in self.cls._meta.related_objects
            if ro.many_to_many
        ]
        m2m_throughs = [
            self.get_through_class(f.remote_field.through)
            for f in self.cls._meta.local_many_to_many
        ]
        return m2m_related_throughs + m2m_throughs

    def get_through_class(self, through):
        if is_str(through):
            module_class = through.rsplit(".", 1)
            class_ = module_class.pop()
            cls_module = self.cls.__module__
            module_path = module_class[0] if module_class else cls_module
            through = getattr(self.find_module(module_path), class_)
        return through

    @staticmethod
    def find_module(module_path):
        if not module_path.endswith(".models"):
            for path in modules.keys():
                if path.endswith(".models") and module_path in path:
                    module_path = path
        return modules[module_path]


def is_str(obj):
    return isinstance(obj, str)


class HistoricalRecordGenerator:
    def __init__(
        self,
        instance,
        history_type,
        user_id,
        user_name,
        ignored_users=None,
        propagate_to_related_fields=True,
        extra_info=None,
    ):
        self.instance = instance
        self.previous_data = getattr(
            from_writable_db(self.instance.history).first(),
            "data",
            None,
        )
        self.history_logging = self.instance._meta.history_logging
        self.history_type = history_type
        self.user_id = user_id
        self.user_name = user_name
        self.ignored_users = ignored_users if ignored_users else {}
        self.propagate_to_related_fields = propagate_to_related_fields
        self.extra_info = extra_info

    def __call__(self):
        if self.should_skip_history_for_user():
            logger.info(
                "Skipping history instance for user '{}' "
                "with user id '{}'".format(
                    self.user_name,
                    self.user_id,
                )
            )
            return
        data = get_instance_field_data(self.instance)
        diff_fields, should_generate_history = self.get_differing_fields(data)
        if not should_generate_history:
            return
        additional_data = get_additional_data(self.instance)
        if self.extra_info:
            additional_data.update(self.extra_info)
        instance_history = HistoricalRecord.objects.create(
            content_object=self.instance,
            history_type=self.history_type,
            history_user=self.user_name,
            history_user_id=self.user_id,
            data=data,
            history_diff=diff_fields,
            additional_data=additional_data,
        )
        if self.propagate_to_related_fields:
            generate_for_related_fields = RelatedFieldHistoryGenerator(
                self.instance,
                instance_history,
                self.previous_data,
            )
            generate_for_related_fields()
        if self.history_logging.interested_related_fields:
            generate_for_interested_objects = InterestedObjectHistoryGenerator(
                self.instance,
                instance_history,
                self.history_logging.interested_related_fields,
                self.previous_data,
            )
            generate_for_interested_objects()

    def should_skip_history_for_user(self):
        ids_to_skip = self.ignored_users.get("user_ids", [])
        user_names_to_skip = self.ignored_users.get("user_names", [])
        return self.user_name in user_names_to_skip or self.user_id in ids_to_skip

    def get_differing_fields(self, data):
        if self.history_type == HistoricalRecord.UPDATE:
            diff_fields = get_diff_fields(
                self.instance,
                data,
                self.previous_data,
                self.history_logging.excluded_fields_names,
            )
            should_generate_history = diff_fields is None or diff_fields
        else:
            diff_fields = list()
            should_generate_history = True
        return diff_fields, should_generate_history


class RelatedFieldHistoryGenerator:
    def __init__(self, instance, instance_history, previous_data):
        self.instance = instance
        self.instance_history = instance_history
        self.history_logging = self.instance._meta.history_logging
        self.previous_data = previous_data

    def __call__(self):
        if self.instance_history.history_type == HistoricalRecord.UPDATE:
            # Make sure the fields_to_check is a list
            # in case history_diff is None.
            fields_to_check = self.instance_history.history_diff or []
        else:
            fields_to_check = list(self.instance_history.data.keys())
        fields_to_check += self.history_logging.excluded_fields_names
        for field_name in fields_to_check:
            try:
                self._generate_for_field(field_name)
            except TypeError:
                continue

    def _generate_for_field(self, field_name):
        field = self.instance._meta.get_field(field_name)
        if not field.is_relation:
            return
        field_value_changed = (
            self.instance_history.history_type
            in (
                HistoricalRecord.UPDATE,
                HistoricalRecord.DELETE,
            ),
        )
        get_related_objects = HistoryEnabledRelatedObjectsCollector(
            self.instance,
            field_name,
            self.previous_data if field_value_changed else None,
        )
        related_objects = get_related_objects()
        for related_object in related_objects:
            generate_history = HistoricalRecordGenerator(
                related_object,
                HistoricalRecord.UPDATE,
                self.instance_history.history_user_id,
                self.instance_history.history_user,
                self.history_logging.get_ignored_users(self.instance),
                # prevent infinite generation of history among related fields.
                propagate_to_related_fields=False,
                extra_info=self.instance_history.additional_data,
            )
            generate_history()


class InterestedObjectHistoryGenerator:
    def __init__(self, instance, instance_history, interested_fields, previous_data):
        self.instance = instance
        self.instance_history = instance_history
        self.interested_fields = interested_fields
        self.previous_data = previous_data

    def __call__(self):
        # Make sure the value changed check is made against
        # an empty list in case history_diff is None
        fields_to_check = self.instance_history.history_diff or []

        for field_name in self.interested_fields:
            field_value_changed = (
                field_name in fields_to_check
                or self.instance_history.history_type == HistoricalRecord.DELETE
            )
            get_related_objects = HistoryEnabledRelatedObjectsCollector(
                self.instance,
                field_name,
                self.previous_data if field_value_changed else None,
            )
            interested_objects = get_related_objects()
            field_changed = field_name in fields_to_check
            for interested_object, status in interested_objects.items():
                # Register any changes to the interested object before the
                # observed object notification is logged into history.
                fake_save(interested_object)
                self.generate_history_for_interested_object(
                    interested_object,
                    status,
                    field_changed,
                )

    def generate_history_for_interested_object(
        self, interested_object, status, field_changed
    ):
        additional_data = get_additional_data(interested_object)
        additional_data.update(self.instance_history.additional_data)
        instance_class_name = self.instance.__class__.__name__
        instance_name = instance_class_name.lower()
        if field_changed and status is HistoryEnabledRelatedObjectsCollector.ADDED:
            action = "Added"
        elif field_changed and status is HistoryEnabledRelatedObjectsCollector.REMOVED:
            action = "Removed"
        else:
            action = self.instance_history.get_history_type_display() + "d"
        additional_data[instance_name] = "{action} {object_type}".format(
            action=action, object_type=instance_class_name
        )
        HistoricalRecord.objects.create(
            content_object=interested_object,
            history_type=HistoricalRecord.UPDATE,
            history_user=self.instance_history.history_user,
            history_user_id=self.instance_history.history_user_id,
            data=get_instance_field_data(interested_object),
            history_diff=[instance_name],
            additional_data=additional_data,
            related_field_history=self.instance_history,
        )


class HistoryEnabledRelatedObjectsCollector:

    ADDED = True
    REMOVED = False
    UNMODIFIED = None

    def __init__(self, instance, field_name, previous_data=None):
        self.instance = instance
        self.field = instance._meta.get_field(field_name)
        if hasattr(self.field, "get_accessor_name"):
            # many-to-* relation fields may have a
            # different accessor name than the field name.
            self.field_name = self.field.get_accessor_name()
        else:
            self.field_name = field_name
        self.previous_data = previous_data

    def __call__(self):
        related_objects = self.get_current_related_objects()
        previous_objects = self.get_previous_objects()
        if self.tracks_history(related_objects + previous_objects):
            result = self.aggregate_related_objects(
                related_objects,
                previous_objects,
            )
        else:
            result = dict()
        return result

    @staticmethod
    def tracks_history(objects):
        return objects and hasattr(objects[0]._meta, "history_logging")

    def get_current_related_objects(self):
        try:
            referenced_object = getattr(self.instance, self.field_name)
        except ObjectDoesNotExist:
            return []
        if self.field.one_to_one or self.field.many_to_one:
            # A single element is guaranteed.
            related_objects = [referenced_object] if referenced_object else []
        elif self.field.one_to_many or self.field.many_to_many:
            # The attribute is a RelatedManager instance.
            related_objects = list(referenced_object.all())
        else:
            raise TypeError(
                "Field {} did not match any known related field types. Known "
                "types: 1-to-1, 1-to-many, many-to-1, many-to-many.".format(self.field)
            )
        return related_objects

    def get_previous_objects(self):
        previous_pks = self.get_previous_object_pks()
        if self.field.related_model:
            model_class = self.field.related_model
        else:
            # The `related_model` field is None on GenericForeignKeys.
            model_content_type = getattr(self.instance, self.field.ct_field)
            model_class = model_content_type.model_class()
        return list(model_class.objects.filter(pk__in=previous_pks))

    def get_previous_object_pks(self):
        if not self.previous_data:
            return list()
        previous_data = self.previous_data.get(self.field_name, None) or ""
        previous_pks = previous_data.split(", ")
        return [pk for pk in previous_pks if pk != ""]

    def aggregate_related_objects(self, related_objects, previous_objects):
        current_objects = set(related_objects)
        previous_objects = set(previous_objects)
        added = current_objects - previous_objects
        unmodified = current_objects & previous_objects
        removed = previous_objects - current_objects
        result = dict(
            [(o, self.ADDED) for o in added]
            + [(o, self.UNMODIFIED) for o in unmodified]
            + [(o, self.REMOVED) for o in removed]
        )
        return result


def get_additional_data(instance):
    history_logging = instance._meta.history_logging
    try:
        additional_data = getattr(
            instance,
            history_logging.additional_data_param_name,
        )
    except AttributeError:
        result = {}
    else:
        result = {key: str(value) for key, value in additional_data.items()}
    return result
