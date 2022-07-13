from django.utils.deprecation import MiddlewareMixin

from atris.models import HistoryLogging


class LoggingRequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        HistoryLogging.thread.request = request
