from __future__ import annotations

import math
import urllib.parse

from yt_dlp.extractor.youtube._streaming.sabr.exceptions import InvalidSabrUrl
from yt_dlp.extractor.youtube._streaming.sabr.models import ConsumedRange
from yt_dlp.utils import int_or_none, parse_qs, str_or_none, traverse_obj, update_url_query


def get_cr_chain(start_consumed_range: ConsumedRange | None, consumed_ranges: list[ConsumedRange]) -> list[ConsumedRange]:
    # Return the continuous consumed range chain starting from the given consumed range
    # Note: It is assumed a segment is only present in one consumed range -
    # it should not be allowed in multiple (by process media header)
    if not start_consumed_range:
        return []
    chain = [start_consumed_range]
    for cr in sorted(consumed_ranges, key=lambda r: r.start_sequence_number):
        if cr.start_sequence_number == chain[-1].end_sequence_number + 1:
            chain.append(cr)
        elif cr.start_sequence_number > chain[-1].end_sequence_number + 1:
            break
    return chain


def find_consumed_range(sequence_number: int, consumed_ranges: list[ConsumedRange]) -> ConsumedRange | None:
    return next(
        (cr for cr in consumed_ranges
         if cr.start_sequence_number <= sequence_number <= cr.end_sequence_number),
        None,
    )


def find_consumed_range_by_time(time_ms: int, consumed_ranges: list[ConsumedRange], tolerance_ms=0) -> ConsumedRange | None:
    for cr in sorted(consumed_ranges, key=lambda _cr: _cr.start_sequence_number):
        if (cr.start_time_ms - tolerance_ms) <= time_ms <= (cr.start_time_ms + cr.duration_ms + tolerance_ms):
            chain = get_cr_chain(cr, consumed_ranges)
            return chain[-1]
    return None


def find_consumed_range_chain(sequence_number: int, consumed_ranges: list[ConsumedRange]) -> list[ConsumedRange]:
    start_cr = find_consumed_range(sequence_number, consumed_ranges)
    return get_cr_chain(start_cr, consumed_ranges)


def fallback_gvs_url(gvs_url):
    """
    Calculate the fallback URL for a given GVS URL using the fvip, mvi, and mn query parameters.

    This only provides the next fallback URL that the server indicates. It does not brute force all possible fallback hosts.

    GVS URL is in the format:

    https://rr?{number}---{mn value}.googlevideo.com/videoplayback?fvip={fvip}&mvi={mvi}&mn={mn}&fallback_count={fallback_count}

    Reference:
    - mvi: original URL number that follows rr/r in the host.
    - fvip: fallback URL number that follows rr/r in the host.
    - mn: comma-separated list of fallback host mn values. The first is the original host.
    - fallback_count: number of fallbacks attempted so far.
        Note this may include fallbacks actioned outside of this function - e.g the server may increment this on SABR_REDIRECT.

    This function simply calculates the next fallback host from the fvip and the fallback hosts in mn.
    """

    def build_host(current_host, f, m):
        rr = current_host.startswith('rr')
        return ('rr' if rr else 'r') + str(f) + '---' + m + '.googlevideo.com'

    qs = parse_qs(gvs_url)
    gvs_url_parsed = urllib.parse.urlparse(gvs_url)
    fvip = int_or_none(qs.get('fvip', [None])[0])
    mvi = int_or_none(qs.get('mvi', [None])[0])
    mn = str_or_none(qs.get('mn', [None])[0], default='').split(',')
    fallback_count = int_or_none(qs.get('fallback_count', ['0'])[0], default=0)

    if fvip is None or mvi is None or not mn:
        return None

    original_host = build_host(gvs_url_parsed.netloc, mvi, mn[0])
    current_host = gvs_url_parsed.netloc

    # No fallback hosts available
    if len(mn) < 2:
        return None

    # Calculate all the possible fallback hosts indicated by the URL parameters.
    fallback_hosts = []
    for mn_entry in mn[1:]:
        fallback_hosts.append(build_host(gvs_url_parsed.netloc, fvip, mn_entry))

    # Find where the current host is in the fallback host list, and return the next one as the fallback URL
    next_host = None
    if current_host == original_host:
        next_host = fallback_hosts[0]
    elif current_host in fallback_hosts:
        current_index = fallback_hosts.index(current_host)
        if current_index < len(fallback_hosts) - 1:
            next_host = fallback_hosts[current_index + 1]

    if not next_host:
        return None

    return update_url_query(
        gvs_url_parsed._replace(netloc=next_host).geturl(), {'fallback_count': fallback_count + 1})


def ticks_to_ms(time_ticks: int, timescale: int):
    if time_ticks is None or timescale is None:
        return None
    return math.ceil((time_ticks / timescale) * 1000)


def broadcast_id_from_url(url: str) -> str | None:
    id_val = parse_qs(url).get('id', [None])[0]
    if id_val is None:
        return None
    return str_or_none(id_val.split('.')[-1])


def validate_sabr_url(url):
    parsed_url = urllib.parse.urlparse(url)

    if not parsed_url.scheme or parsed_url.scheme != 'https':
        raise InvalidSabrUrl('not a valid https url', url)

    if not parsed_url.netloc.endswith('.googlevideo.com') or parsed_url.netloc == 'googlevideo.com':
        raise InvalidSabrUrl('not a valid googlevideo url', url)

    # Check if the query params include sabr=1
    sabr_query = urllib.parse.parse_qs(parsed_url.query).get('sabr')
    if traverse_obj(sabr_query, (0, {str})) != '1':
        raise InvalidSabrUrl('missing sabr=1 parameter', url)

    return url
