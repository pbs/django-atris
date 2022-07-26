from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import connections, models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from atris.models import ArchivedHistoricalRecord, HistoricalRecord, history_logging


class ContentTypeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Content type")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "content_type"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        followed_content_types = [
            ContentType.objects.get_for_model(model)
            for model in history_logging.registered_models.keys()
        ]

        filter_results = set()
        for content_type in followed_content_types:
            filter_results.add((content_type.id, _(content_type.model)))

        return filter_results

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() is not None:
            return queryset.filter(content_type__id=self.value())


class ApproxCountPgQuerySet(models.query.QuerySet):
    """approximate unconstrained count(*) with reltuples from pg_class"""

    def count(self):
        if hasattr(connections[self.db].client.connection, "pg_version"):
            query = self.query
            no_filtration_used = (
                not query.where
                and query.high_mark is None
                and query.low_mark == 0
                and not query.select
                and not query.group_by
                and not query.having
                and not query.distinct
            )
            if no_filtration_used:
                parts = [p.strip('"') for p in self.model._meta.db_table.split(".")]
                if 1 <= len(parts) <= 2:
                    cursor = connections[self.db].cursor()
                    if len(parts) == 1:
                        cursor.execute(
                            "SELECT reltuples::bigint "
                            "FROM pg_class "
                            "WHERE relname = %s",
                            parts,
                        )
                    else:
                        cursor.execute(
                            "SELECT reltuples::bigint "
                            "FROM pg_class c "
                            "JOIN pg_namespace n on (c.relnamespace = n.oid) "
                            "WHERE n.nspname = %s AND c.relname = %s",
                            parts,
                        )
                    return cursor.fetchall()[0][0]
        return self.query.get_count(using=self.db)


class GenericHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "object_id",
        "content_type",
        "history_date",
        "history_type",
        "history_user",
    )

    fields = [
        "object_id",
        "content_type",
        "history_date",
        "history_type",
        "history_user",
        "difference_to_previous",
        "fields_that_differ",
        "history_snapshot",
        "more_info",
        "related_field_history_admin",
    ]

    readonly_fields = fields

    search_fields = ("object_id",)

    list_filter = (ContentTypeListFilter, "history_type")

    show_full_result_count = False

    def get_queryset(self, request):
        # Capturing the request object in order to build the absolute URI in
        # `related_field_history_admin`
        self._request = request
        qs = super().get_queryset(request)
        return qs

    def history_snapshot(self, obj):
        return self._dict_to_table(obj.data)

    def more_info(self, obj):
        return self._dict_to_table(obj.additional_data)

    def difference_to_previous(self, obj):
        return obj.get_diff_to_prev_string()

    def fields_that_differ(self, obj):
        if obj.history_diff:
            return ", ".join(obj.history_diff)
        return None

    def _dict_to_table(self, dictionary):
        table = (
            '<table style="border: 1px solid #eee;">'
            + "".join(
                [
                    '<tr><td style="border: 1px solid #eee;">{}</td> <td>{}'
                    "</td></tr>".format(
                        key,
                        val,
                    )
                    for (key, val) in dictionary.items()
                ]
            )
            + "</table>"
        )

        return mark_safe(table)

    def related_field_history_admin(self, obj):
        if obj.related_field_history:
            related_url = reverse(
                "admin:atris_historicalrecord_change",
                args=[obj.related_field_history.pk],
            )
            absolute_uri = self._request.build_absolute_uri(related_url)
            related_object_model = obj.related_field_history.content_type.model
            html = '<a href="{}">{}</a>'.format(
                absolute_uri,
                obj.additional_data[related_object_model],
            )
            return mark_safe(html)
        else:
            return "--"

    related_field_history_admin.short_description = "Related Field History"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class HistoricalRecordAdmin(GenericHistoryAdmin):
    model = HistoricalRecord
    show_full_result_count = False


class ArchivedHistoricalRecordAdmin(GenericHistoryAdmin):
    model = ArchivedHistoricalRecord
    show_full_result_count = False


admin.site.register(HistoricalRecord, HistoricalRecordAdmin)
admin.site.register(ArchivedHistoricalRecord, ArchivedHistoricalRecordAdmin)
