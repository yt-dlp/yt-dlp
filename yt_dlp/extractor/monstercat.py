import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    int_or_none,
    strip_or_none,
    unified_strdate,
)
from ..utils.traversal import find_element, traverse_obj


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
            'album_artists': ['BT'],
        },
    }]

    def _extract_tracks(self, table, album_meta):
        for td in re.findall(r'<tr[^<]*>((?:(?!</tr>)[\w\W])+)', table):  # regex by chatgpt due to lack of get_elements_by_tag
            title = traverse_obj(td, (
                {find_element(cls='d-inline-flex flex-column')},
                {lambda x: x.partition(' <span')}, 0, {clean_html}))
            ids = traverse_obj(td, (
                {find_element(cls='btn-play cursor-pointer mr-small', html=True)}, {extract_attributes})) or {}
            track_id = ids.get('data-track-id')
            release_id = ids.get('data-release-id')

            track_number = traverse_obj(td, ({find_element(cls='py-xsmall')}, {int_or_none}))
            if not track_id or not release_id:
                self.report_warning(f'Skipping track {track_number}, ID(s) not found')
                self.write_debug(f'release_id={release_id!r} track_id={track_id!r}')
                continue
            yield {
                **album_meta,
                'title': title,
                'track': title,
                'track_number': track_number,
                'artists': traverse_obj(td, ({find_element(cls='d-block fs-xxsmall')}, {clean_html}, all)),
                'url': f'https://www.monstercat.com/api/release/{release_id}/track-stream/{track_id}',
                'id': track_id,
                'ext': 'mp3',
            }

    def _real_extract(self, url):
        url_id = self._match_id(url)
        html = self._download_webpage(url, url_id)
        # NB: HTMLParser may choke on this html; use {find_element} or try_call(lambda: get_element...)
        tracklist_table = traverse_obj(html, {find_element(cls='table table-small')}) or ''
        title = traverse_obj(html, ({find_element(tag='h1')}, {clean_html}))

        album_meta = {
            'title': title,
            'album': title,
            'thumbnail': f'https://www.monstercat.com/release/{url_id}/cover',
            'album_artists': traverse_obj(html, (
                {find_element(cls='h-normal text-uppercase mb-desktop-medium mb-smallish')}, {clean_html}, all)),
            'release_date': traverse_obj(html, (
                {find_element(cls='font-italic mb-medium d-tablet-none d-phone-block')},
                {lambda x: x.partition('Released ')}, 2, {strip_or_none}, {unified_strdate})),
        }

        return self.playlist_result(
            self._extract_tracks(tracklist_table, album_meta), playlist_id=url_id, **album_meta)
