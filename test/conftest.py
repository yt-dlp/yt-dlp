import inspect

import pytest

from yt_dlp.networking import RequestHandler
from yt_dlp.networking.common import _REQUEST_HANDLERS
from yt_dlp.utils._utils import _YDLLogger as FakeLogger


@pytest.fixture
def handler(request):
    RH_KEY = getattr(request, 'param', None)
    if not RH_KEY:
        return
    if inspect.isclass(RH_KEY) and issubclass(RH_KEY, RequestHandler):
        handler = RH_KEY
    elif RH_KEY in _REQUEST_HANDLERS:
        handler = _REQUEST_HANDLERS[RH_KEY]
    else:
        pytest.skip(f'{RH_KEY} request handler is not available')

    class HandlerWrapper(handler):
        RH_KEY = handler.RH_KEY

        def __init__(self, **kwargs):
            super().__init__(logger=FakeLogger, **kwargs)

    return HandlerWrapper


@pytest.fixture(autouse=True)
def skip_handler(request, handler):
    """usage: pytest.mark.skip_handler('my_handler', 'reason')"""
    for marker in request.node.iter_markers('skip_handler'):
        if marker.args[0] == handler.RH_KEY:
            pytest.skip(marker.args[1] if len(marker.args) > 1 else '')


@pytest.fixture(autouse=True)
def skip_handler_if(request, handler):
    """usage: pytest.mark.skip_handler_if('my_handler', lambda request: True, 'reason')"""
    for marker in request.node.iter_markers('skip_handler_if'):
        if marker.args[0] == handler.RH_KEY and marker.args[1](request):
            pytest.skip(marker.args[2] if len(marker.args) > 2 else '')


@pytest.fixture(autouse=True)
def skip_handlers_if(request, handler):
    """usage: pytest.mark.skip_handlers_if(lambda request, handler: True, 'reason')"""
    for marker in request.node.iter_markers('skip_handlers_if'):
        if handler and marker.args[0](request, handler):
            pytest.skip(marker.args[1] if len(marker.args) > 1 else '')


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'skip_handler(handler): skip test for the given handler',
    )
    config.addinivalue_line(
        'markers', 'skip_handler_if(handler): skip test for the given handler if condition is true',
    )
    config.addinivalue_line(
        'markers', 'skip_handlers_if(handler): skip test for handlers when the condition is true',
    )
