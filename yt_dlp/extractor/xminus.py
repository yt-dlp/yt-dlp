import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    int_or_none,
    merge_dicts,
    parse_bitrate,
    parse_count,
    parse_duration,
    parse_filesize,
    str_or_none,
    unified_strdate,
    update_url_query,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    require,
    traverse_obj,
    trim_str,
    unpack,
)


class XMinusIE(InfoExtractor):
    IE_NAME = 'xminus'
    IE_DESC = 'X-Minus'

    _VALID_URL = r'https?://x-minus\.pro/track/(?P<id>\d+)/[^/?#]+'
    _TESTS = [{
        'url': 'https://x-minus.pro/track/4542/%D0%BF%D0%B5%D1%81%D0%B5%D0%BD%D0%BA%D0%B0-%D1%88%D0%BE%D1%84%D1%91%D1%80%D0%B0-2',
        'info_dict': {
            'id': '4542',
            'ext': 'mp3',
            'title': 'Песенка шофёра',
            'alt_title': 'Instrumental #2',
            'artists': ['Леонид Агутин'],
            'description': 'md5:ed26c57333e7e6dc002ff118c5ac419a',
            'duration': 156,
            'like_count': int,
            'upload_date': '20120906',
            'view_count': int,
        },
    }, {
        'url': 'https://x-minus.pro/track/389368/%D0%BA%D1%80%D0%B8%D0%BB%D0%B0',
        'info_dict': {
            'id': '389368',
            'ext': 'mp3',
            'title': 'Крила',
            'alt_title': 'Instrumental',
            'artists': ['Jamala'],
            'description': 'md5:c3a0029c81a71fad31d451f42e958768',
            'duration': 263,
            'genres': ['arrangement'],
            'like_count': int,
            'tags': ['Pop songs', 'Pop'],
            'upload_date': '20190125',
            'uploader': 'BeKhan',
            'uploader_id': '374800',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        track_id = self._match_id(url)
        webpage = self._download_webpage(
            url, track_id, query={'locale': 'en_US'})

        player_attrs = traverse_obj(webpage, (
            {find_element(id=f'm{track_id}', html=True)}, {extract_attributes}))
        prefix = traverse_obj(player_attrs, ('data-k', {str}, {require('data-k')}))
        is_updated = bool(traverse_obj(player_attrs, ('data-updated', {str})))

        data_k = traverse_obj(webpage, (
            {find_element(id='player-data', html=True)},
            {extract_attributes}, 'data-k', {str}, {require('data-k')}))
        data_fn = traverse_obj(webpage, (
            {find_element(id=f'dw-link-m{track_id}')},
            {find_element(cls='no-ajax', html=True)},
            {extract_attributes}, 'data-fn', {str}, {require('data-fn')}))

        track_id_int = int(track_id)
        subdomain = 'm5' if is_updated or track_id_int >= 782_788 else 'm4'
        s = sum(map(ord, data_k)) + track_id_int + 1004
        c = int((track_id_int - 125_765) / 333)
        query = {
            't668': f'{s:x}zyxwz{track_id}.9z{prefix}z{c}',
        }
        if is_updated:
            query['updated'] = '1'

        file_url = update_url_query(
            f'https://{subdomain}.xmst.cc/dl/minus/{track_id}', query)
        file_url += '&trackname=' + urllib.parse.quote(data_fn, safe="!'()*")

        info = traverse_obj(webpage, (
            {find_element(cls='minustrack-info', html=True)},
            {re.compile(r'<tr[^>]*>([\s\S]+?)</tr>').findall}, ...,
            {lambda x: dict([map(str.strip, clean_html(x).split(':', 1))])},
            all, {unpack(merge_dicts)}))
        filesize, bitrate = re.match(r'(.+)\s+(\d+\s*kbps)', info.get('File Size')).groups()
        date_str = info.get('Uploaded', '').split('@', 1)[-1].strip()

        return {
            'id': track_id,
            'ext': 'mp3',
            'filesize_approx': parse_filesize(filesize),
            'genres': traverse_obj(info, ('Type', {str_or_none}, filter, all, filter)),
            'tbr': parse_bitrate(bitrate),
            'upload_date': unified_strdate(date_str) if date_str else None,
            'url': file_url,
            'vcodec': 'none',
            **traverse_obj(webpage, {
                'title': ({find_element(cls='list in-tab tracklist', html=True)},
                          {extract_attributes}, 'data-tit', {clean_html}, filter),
                'alt_title': ({find_element(cls='minustrack-full-title')},
                              {find_element(cls='hide-mob')}, {clean_html}, filter),
                'artists': ({find_element(cls='card-tit notranslate')},
                            {find_element(tag='a')}, {clean_html}, filter, all, filter),
                'description': ({find_element(cls='tab-lyrics notranslate')}, {clean_html}, filter),
                'duration': ({find_element(cls='player-duration')}, {parse_duration}),
                'like_count': ({find_element(cls='button-like-value')}, {int_or_none}),
                'tags': ({find_elements(cls='minustrack-info-tag')}, ..., {clean_html}, filter, all, filter),
                'view_count': ({find_element(attr='data-tooltip', value='Track rating for all time')}, {clean_html}, {parse_count}),
            }),
            **traverse_obj(webpage, ({find_element(cls='minustrack-info-user', html=True)}, {
                'uploader': ({clean_html}, filter),
                'uploader_id': ({extract_attributes}, 'href', {trim_str(start='/user/')}),
            })),
        }
