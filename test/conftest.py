import functools
import inspect

import pytest

from yt_dlp.networking import RequestHandler
from yt_dlp.networking.common import _REQUEST_HANDLERS
from yt_dlp.utils._utils import _YDLLogger as FakeLogger
