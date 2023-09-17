import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    int_or_none,
    unified_strdate,
    strip_or_none,
    traverse_obj,
)


class MonstercatIE(InfoExtractor):
    _VALID_URL = r'https://www\.monstercat\.com/release/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.monstercat.com/release/742779548009',
        'playlist_count': 20,
        'info_dict': {
            'title': 'The Secret Language of Trees',
            'id': '742779548009',
            'thumbnail': 'https://www.monstercat.com/release/742779548009/cover',
            'release_year': 2023,
            'release_date': '20230711',
            'album': 'The Secret Language of Trees',
            'album_artist': 'BT',
        }
    }]

    TRACK_API = 'https://www.monstercat.com/api/release/{release_id}/track-stream/{song_id}'

    def _extract_tracks(self, table, album_meta):
        for td in re.findall(r'<tr[^<]*>((?:(?!</tr>)[\w\W])+)', table):  # regex by chatgpt due to lack of get_elements_by_tag
            title = traverse_obj(get_element_by_class('d-inline-flex flex-column', td).partition(' <span'), (0, {strip_or_none}))
            ids = traverse_obj(get_element_html_by_class('btn-play cursor-pointer mr-small', td), {extract_attributes})
            yield {
                **album_meta,
                'title': title,
                'track': title,
                'track_number': traverse_obj(get_element_by_class('py-xsmall', td), {int_or_none}),
                'artist': traverse_obj(td, {lambda td: get_element_by_class('d-block fs-xxsmall', td)}),
                'url': self.TRACK_API.format(release_id=ids.get('data-release-id'),
                                             song_id=ids.get('data-track-id')),
                'id': ids.get('data-track-id'),
                'ext': 'mp3'
            }

    def _real_extract(self, url):
        url_id = self._match_id(url)
        html = self._download_webpage(url, url_id)
        tracklist_table = traverse_obj(html, {lambda html: get_element_by_class('table table-small', html)})

        title = traverse_obj(get_element_text_and_html_by_tag('h1', html), 0)
        date = traverse_obj(html, ({lambda html: get_element_by_class('font-italic mb-medium d-tablet-none d-phone-block',
                            html).partition('Released ')}, 2, {strip_or_none}, {unified_strdate}))

        album_meta = {
            'title': title,
            'album': title,
            'thumbnail': url + '/cover',
            'album_artist': traverse_obj(html, {lambda html: get_element_by_class('h-normal text-uppercase mb-desktop-medium mb-smallish', html)}),
            'release_year': traverse_obj(date, ({lambda x: date[:4]}, {int_or_none})),
            'release_date': date,
        }

        return self.playlist_result(self._extract_tracks(tracklist_table, album_meta),
                                    playlist_id=url_id, **album_meta)
