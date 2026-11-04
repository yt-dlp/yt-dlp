import pytest
from yt_dlp.downloader.sabr import SabrFD


@pytest.mark.parametrize('requested_formats, expected', [
    ([{'protocol': 'sabr'}, {'protocol': 'sabr'}], True),
    ([{'protocol': 'http'}, {'protocol': 'https'}], False),
    ([{'protocol': 'http'}, {'protocol': 'sabr'}], False),
    (None, False),
], ids=['all sabr', 'no sabr', 'mixed protocols', 'none'])
def test_can_download_requested_formats(ydl, requested_formats, expected):
    fd = SabrFD(ydl, {})
    info_dict = {'requested_formats': requested_formats}
    assert fd.can_download(info_dict) is expected


@pytest.mark.parametrize('info_dict,expected', [
    ({'protocol': 'http'}, False),
    ({'protocol': 'sabr'}, True),
    ({}, False),
], ids=['not sabr', 'sabr', 'none'])
def test_can_download_single_format(ydl, info_dict, expected):
    fd = SabrFD(ydl, {})
    assert fd.can_download(info_dict) is expected
