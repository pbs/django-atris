from atris.models import HistoryLogging


class LoggingRequestMiddleware(object):

    def process_request(self, request):
        HistoryLogging.thread.request = request
