import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    int_or_none,
    strip_or_none,
    traverse_obj,
    try_call,
    unified_strdate,
)


class MonstercatIE(InfoExtractor):
    _VALID_URL = r'https?://www\.monstercat\.com/release/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.monstercat.com/release/742779548009',
        'playlist_count': 20,
        'info_dict': {
            'title': 'The Secret Language of Trees',
            'id': '742779548009',
            'thumbnail': 'https://www.monstercat.com/release/742779548009/cover',
            'release_date': '20230711',
            'album': 'The Secret Language of Trees',
            'album_artist': 'BT',
        },
    }]

    def _extract_tracks(self, table, album_meta):
        for td in re.findall(r'<tr[^<]*>((?:(?!</tr>)[\w\W])+)', table):  # regex by chatgpt due to lack of get_elements_by_tag
            title = clean_html(try_call(
                lambda: get_element_by_class('d-inline-flex flex-column', td).partition(' <span')[0]))
            ids = extract_attributes(try_call(lambda: get_element_html_by_class('btn-play cursor-pointer mr-small', td)) or '')
            track_id = ids.get('data-track-id')
            release_id = ids.get('data-release-id')

            track_number = int_or_none(try_call(lambda: get_element_by_class('py-xsmall', td)))
            if not track_id or not release_id:
                self.report_warning(f'Skipping track {track_number}, ID(s) not found')
                self.write_debug(f'release_id={release_id!r} track_id={track_id!r}')
                continue
            yield {
                **album_meta,
                'title': title,
                'track': title,
                'track_number': track_number,
                'artist': clean_html(try_call(lambda: get_element_by_class('d-block fs-xxsmall', td))),
                'url': f'https://www.monstercat.com/api/release/{release_id}/track-stream/{track_id}',
                'id': track_id,
                'ext': 'mp3',
            }

    def _real_extract(self, url):
        url_id = self._match_id(url)
        html = self._download_webpage(url, url_id)
        # wrap all `get_elements` in `try_call`, HTMLParser has problems with site's html
        tracklist_table = try_call(lambda: get_element_by_class('table table-small', html)) or ''

        title = try_call(lambda: get_element_text_and_html_by_tag('h1', html)[0])
        date = traverse_obj(html, ({lambda html: get_element_by_class('font-italic mb-medium d-tablet-none d-phone-block',
                            html).partition('Released ')}, 2, {strip_or_none}, {unified_strdate}))

        album_meta = {
            'title': title,
            'album': title,
            'thumbnail': f'https://www.monstercat.com/release/{url_id}/cover',
            'album_artist': try_call(
                lambda: get_element_by_class('h-normal text-uppercase mb-desktop-medium mb-smallish', html)),
            'release_date': date,
        }

        return self.playlist_result(
            self._extract_tracks(tracklist_table, album_meta), playlist_id=url_id, **album_meta)
