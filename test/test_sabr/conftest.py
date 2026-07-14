from unittest.mock import MagicMock
import pytest

pytest.importorskip('protobug', reason='protobug is not installed')

from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, ClientName
from yt_dlp.extractor.youtube._streaming.sabr.models import SabrLogger


@pytest.fixture
def logger():
    mock_logger = MagicMock()
    mock_logger.LogLevel = SabrLogger.LogLevel
    mock_logger.log_level = SabrLogger.LogLevel.TRACE
    return mock_logger


@pytest.fixture
def client_info():
    return ClientInfo(client_name=ClientName.WEB)
