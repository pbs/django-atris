from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from atris.models import HistoricalRecord
from atris.models import history_logging
from atris.models.archived_historical_record import ArchivedHistoricalRecord


class ContentTypeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Content type')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'content_type'

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


class GenericHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'object_id', 'content_type', 'history_date', 'history_type',
        'history_user'
    )
    fields = ['object_id', 'content_type', 'history_date', 'history_type',
              'history_user', 'difference_to_previous', 'fields_that_differ',
              'history_snapshot', 'more_info']

    readonly_fields = fields

    search_fields = ('object_id',)

    list_filter = (ContentTypeListFilter, 'history_type')

    def history_snapshot(self, obj):
        return self._dict_to_table(obj.data)

    def more_info(self, obj):
        return self._dict_to_table(obj.additional_data)

    def difference_to_previous(self, obj):
        return obj.get_diff_to_prev_string()

    def fields_that_differ(self, obj):
        if obj.history_diff:
            return ','.join(obj.history_diff)
        return None

    def _dict_to_table(self, dict):
        table = '<table style="border: 1px solid #eee;">' + ''.join(
            [
                '<tr><td style="border: 1px solid #eee;">{}</td> <td>{'
                '}</td></tr>'.format(
                    key, val)
                for (key, val) in dict.items()]
        ) + '</table>'

        return mark_safe(table)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class HistoricalRecordAdmin(GenericHistoryAdmin):
    model = HistoricalRecord


class ArchivedHistoricalRecordAdmin(GenericHistoryAdmin):
    model = ArchivedHistoricalRecord


admin.site.register(HistoricalRecord, HistoricalRecordAdmin)
admin.site.register(ArchivedHistoricalRecord, ArchivedHistoricalRecordAdmin)
