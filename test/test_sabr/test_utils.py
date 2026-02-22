from __future__ import annotations

import re

import pytest

from yt_dlp.extractor.youtube._streaming.sabr.exceptions import InvalidSabrUrl
from yt_dlp.extractor.youtube._streaming.sabr.utils import ticks_to_ms, broadcast_id_from_url, validate_sabr_url, fallback_gvs_url
from yt_dlp.extractor.youtube._streaming.sabr.utils import (
    get_cr_chain,
    find_consumed_range,
    find_consumed_range_chain,
)
from yt_dlp.extractor.youtube._streaming.sabr.models import ConsumedRange


def _make_cr(start, end, start_time_ms=0, duration_ms=1000):
    return ConsumedRange(start_sequence_number=start, end_sequence_number=end, start_time_ms=start_time_ms, duration_ms=duration_ms)


class TestConsumedRangeUtils:
    def test_get_cr_chain_none_start_returns_empty(self):
        assert get_cr_chain(None, []) == []

    def test_find_consumed_range_not_found_returns_none(self):
        crs = [_make_cr(1, 2), _make_cr(4, 5)]
        assert find_consumed_range(3, crs) is None

    def test_find_consumed_range_found(self):
        cr = _make_cr(1, 3)
        crs = [cr]
        assert find_consumed_range(2, crs) is cr

    def test_get_cr_chain_contiguous_and_stop_on_gap(self):
        cr1 = _make_cr(1, 2)
        cr2 = _make_cr(3, 4)
        cr3 = _make_cr(5, 6)
        crs = [cr1, cr2, cr3]

        chain = get_cr_chain(cr1, crs)
        assert chain == [cr1, cr2, cr3]

        cr_gap = _make_cr(7, 8)
        crs_gap = [cr1, cr2, cr_gap]
        chain2 = get_cr_chain(cr1, crs_gap)
        assert chain2 == [cr1, cr2]

    def test_find_consumed_range_chain_from_middle_sequence(self):
        a = _make_cr(1, 1)
        b = _make_cr(2, 2)
        c = _make_cr(3, 4)
        crs = [a, b, c]

        chain = find_consumed_range_chain(2, crs)
        assert chain == [b, c]

        chain_all = find_consumed_range_chain(1, crs)
        assert chain_all == [a, b, c]

        assert find_consumed_range_chain(10, crs) == []


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
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example.1~243&other2=param2') == '1~243'
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example') == 'example'
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example.3&other2=param2') == '3'
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example.3.2&other2=param2') == '2'
    assert broadcast_id_from_url('https://example.com/path?other=param&other2=param2') is None


class TestValidateSabrUrl:

    @pytest.mark.parametrize('url, error', [
        (None, 'not a valid https url'),
        ('', 'not a valid https url'),
        ('bad-url%', 'not a valid https url'),
        ('http://test.googlevideo.com?sabr=1', 'not a valid https url'),
        ('file:///etc/passwd', 'not a valid https url'),

        ('https://test.example.com?sabr=1', 'not a valid googlevideo url'),
        ('https://test.googlevideo.com.example.com?sabr=1', 'not a valid googlevideo url'),
        ('https://test.googlevideo.co?sabr=1', 'not a valid googlevideo url'),
        ('https://googlevideo.com?sabr=1', 'not a valid googlevideo url'),

        ('https://test.googlevideo.com', 'missing sabr=1 parameter'),
        ('https://test.googlevideo.com?sabr=', 'missing sabr=1 parameter'),
        ('https://test.googlevideo.com?sabr=0', 'missing sabr=1 parameter'),
        ('https://test.googlevideo.com?sabr=0&sabr=1', 'missing sabr=1 parameter'),
    ])
    def test_invalid_sabr_url(self, url, error):
        with pytest.raises(InvalidSabrUrl, match=rf'Invalid SABR URL: {error} \(url={re.escape(str(url))}\)'):
            validate_sabr_url(url)

    @pytest.mark.parametrize('url', [
        'https://test.googlevideo.com?sabr=1',
        'https://sub.test.googlevideo.com?sabr=1',
        'https://ss1--1234xyz-bbbb.googlevideo.com?sabr=1',
        'https://test.googlevideo.com?other=xyz&sabr=1&test=yes',
        'https://test.googlevideo.com?other=xyz&sabr=1&test=yes&sabr=0',
    ])
    def test_valid_sabr_url(self, url):
        assert validate_sabr_url(url) == url


@pytest.mark.parametrize('url, expected', [
    # No fallback
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1&fvip=5', None),

    # Single fallback
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2&fvip=5', 'https://rr5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2&fvip=5&fallback_count=1'),
    ('https://rr5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2&fvip=5&fallback_count=1', None),

    # Multiple fallbacks
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5', 'https://rr5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=1'),
    ('https://rr5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=1', 'https://rr5---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=2'),
    ('https://rr5---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=2', None),

    # Single r with multiple fallbacks
    ('https://r1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5', 'https://r5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=1'),
    ('https://r5---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=1', 'https://r5---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=2'),
    ('https://r5---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5&fallback_count=2', None),

    # Missing fvip - should not fallback
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=', None),
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3', None),

    # Missing mn - should not fallback
    ('https://rr1---host1.googlevideo.com?mvi=1&fvip=5', None),

    # Does not start with r or rr - should not fallback
    ('https://x1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5', None),
    ('https://rrr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=5', None),

    # Missing mvi - should not fallback
    ('https://rr1---host1.googlevideo.com?mn=host1%2Chost2%2Chost3&fvip=5', None),

    # fvip is same as mvi - should fallback to next host
    ('https://rr1---host1.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=1', 'https://rr1---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=1&fallback_count=1'),
    ('https://rr1---host2.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=1&fallback_count=1', 'https://rr1---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=1&fallback_count=2'),
    ('https://rr1---host3.googlevideo.com?mvi=1&mn=host1%2Chost2%2Chost3&fvip=1&fallback_count=2', None),
])
def test_fallback_url(url, expected):
    assert fallback_gvs_url(url) == expected
