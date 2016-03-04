from atris.models import HistoricalRecord
from atris.models.archived_historical_record import ArchivedHistoricalRecord
from django.contrib import admin
from django.utils.safestring import mark_safe


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

    list_filter = (('content_type', admin.RelatedOnlyFieldListFilter),
                   'history_type')

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
