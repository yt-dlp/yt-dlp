from __future__ import annotations

import contextlib
import math
import urllib.parse

from yt_dlp.extractor.youtube._streaming.sabr.models import ConsumedRange
from yt_dlp.utils import int_or_none, orderedSet, parse_qs, str_or_none, update_url_query


def get_cr_chain(start_consumed_range: ConsumedRange, consumed_ranges: list[ConsumedRange]) -> list[ConsumedRange]:
    # TODO: unit test
    # Return the continuous consumed range chain starting from the given consumed range
    # Note: It is assumed a segment is only present in one consumed range - it should not be allowed in multiple (by process media header)
    chain = [start_consumed_range]
    for cr in sorted(consumed_ranges, key=lambda r: r.start_sequence_number):
        if cr.start_sequence_number == chain[-1].end_sequence_number + 1:
            chain.append(cr)
        elif cr.start_sequence_number > chain[-1].end_sequence_number + 1:
            break
    return chain


def next_gvs_fallback_url(gvs_url):
    # TODO: unit test
    qs = parse_qs(gvs_url)
    gvs_url_parsed = urllib.parse.urlparse(gvs_url)
    fvip = int_or_none(qs.get('fvip', [None])[0])
    mvi = int_or_none(qs.get('mvi', [None])[0])
    mn = str_or_none(qs.get('mn', [None])[0], default='').split(',')
    fallback_count = int_or_none(qs.get('fallback_count', ['0'])[0], default=0)

    hosts = []

    def build_host(current_host, f, m):
        rr = current_host.startswith('rr')
        if f is None or m is None:
            return None
        return ('rr' if rr else 'r') + str(f) + '---' + m + '.googlevideo.com'

    original_host = build_host(gvs_url_parsed.netloc, mvi, mn[0])

    # Order of fallback hosts:
    # 1. Fallback host in url (mn[1] + fvip)
    # 2. Fallback hosts brute forced (this usually contains the original host)
    for mn_entry in reversed(mn):
        for fvip_entry in orderedSet([fvip, 1, 2, 3, 4, 5]):
            fallback_host = build_host(gvs_url_parsed.netloc, fvip_entry, mn_entry)
            if fallback_host and fallback_host not in hosts:
                hosts.append(fallback_host)

    if not hosts or len(hosts) == 1:
        return None

    # if first fallback, anchor to start of list so we start with the known fallback hosts
    # Sometimes we may get a SABR_REDIRECT after a fallback, which gives a new host with new fallbacks.
    # In this case, the original host indicated by the url params would match the current host
    current_host_index = -1
    if fallback_count > 0 and gvs_url_parsed.netloc != original_host:
        with contextlib.suppress(ValueError):
            current_host_index = hosts.index(gvs_url_parsed.netloc)

    def next_host(idx, h):
        return h[(idx + 1) % len(h)]

    new_host = next_host(current_host_index + 1, hosts)
    # If the current URL only has one fallback host, then the first fallback host is the same as the current host.
    if new_host == gvs_url_parsed.netloc:
        new_host = next_host(current_host_index + 2, hosts)

    # TODO: do not return new_host if it still matches the original host
    return update_url_query(
        gvs_url_parsed._replace(netloc=new_host).geturl(), {'fallback_count': fallback_count + 1})


def ticks_to_ms(time_ticks: int, timescale: int):
    if time_ticks is None or timescale is None:
        return None
    return math.ceil((time_ticks / timescale) * 1000)


def broadcast_id_from_url(url: str) -> str | None:
    return str_or_none(parse_qs(url).get('id', [None])[0])
