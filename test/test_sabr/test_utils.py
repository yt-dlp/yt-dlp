from __future__ import annotations

import pytest
from yt_dlp.extractor.youtube._streaming.sabr.utils import ticks_to_ms, broadcast_id_from_url
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
    assert broadcast_id_from_url('https://example.com/path?other=param&id=example.1~243&other2=param2') == 'example.1~243'
    assert broadcast_id_from_url('https://example.com/path?other=param&other2=param2') is None
