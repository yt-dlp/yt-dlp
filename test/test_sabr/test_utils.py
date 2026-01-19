import pytest
from yt_dlp.extractor.youtube._streaming.sabr.utils import ticks_to_ms, broadcast_id_from_url


@pytest.mark.parametrize(
    'ticks, timescale, expected_ms',
    [
        (1000, 1000, 1000),
        (5000, 10000, 500),
        (234234, 44100, 5312),
        (1, 1, 1000),
        (None, 1000, None),
        (1000, None, None),
        (None, None, None),
    ],
)
def test_ticks_to_ms(ticks, timescale, expected_ms):
    assert ticks_to_ms(ticks, timescale) == expected_ms


def test_broadcast_id_from_url():
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example.1~243&other2=param2') == 'example.1~243'
    assert broadcast_id_from_url('https://example.com/path?other=param&other2=param2') is None
