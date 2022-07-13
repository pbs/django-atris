from pytest import fixture

from atris.middleware import LoggingRequestMiddleware
from atris.models import HistoryLogging


@fixture(scope="function")
def mock_request(mocker):
    request = mocker.Mock()
    request.path = "/testURL/"
    request.session = {}
    return request


def test_logging_request_middleware(mock_request):
    assert not hasattr(HistoryLogging.thread, "request")
    middleware = LoggingRequestMiddleware()
    middleware.process_request(mock_request)
    assert HistoryLogging.thread.request == mock_request
