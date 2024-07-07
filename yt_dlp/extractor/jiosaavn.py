import functools
import math
import re

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    clean_html,
    int_or_none,
    make_archive_id,
    smuggle_url,
    unsmuggle_url,
    url_basename,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class JioSaavnBaseIE(InfoExtractor):
    _API_URL = 'https://www.jiosaavn.com/api.php'
    _VALID_BITRATES = {'16', '32', '64', '128', '320'}

    @functools.cached_property
    def requested_bitrates(self):
        requested_bitrates = self._configuration_arg('bitrate', ['128', '320'], ie_key='JioSaavn')
        if invalid_bitrates := set(requested_bitrates) - self._VALID_BITRATES:
            raise ValueError(
                f'Invalid bitrate(s): {", ".join(invalid_bitrates)}. '
                f'Valid bitrates are: {", ".join(sorted(self._VALID_BITRATES, key=int))}')
        return requested_bitrates

    def _extract_formats(self, song_data):
        for bitrate in self.requested_bitrates:
            media_data = self._download_json(
                self._API_URL, song_data['id'],
                f'Downloading format info for {bitrate}',
                fatal=False, data=urlencode_postdata({
                    '__call': 'song.generateAuthToken',
                    '_format': 'json',
                    'bitrate': bitrate,
                    'url': song_data['encrypted_media_url'],
                }))
            if not traverse_obj(media_data, ('auth_url', {url_or_none})):
                self.report_warning(f'Unable to extract format info for {bitrate}')
                continue
            ext = media_data.get('type')
            yield {
                'url': media_data['auth_url'],
                'ext': 'm4a' if ext == 'mp4' else ext,
                'format_id': bitrate,
                'abr': int(bitrate),
                'vcodec': 'none',
            }

    def _extract_song(self, song_data, url=None):
        info = traverse_obj(song_data, {
            'id': ('id', {str}),
            'title': ('song', {clean_html}),
            'album': ('album', {clean_html}),
            'thumbnail': ('image', {url_or_none}, {lambda x: re.sub(r'-\d+x\d+\.', '-500x500.', x)}),
            'duration': ('duration', {int_or_none}),
            'view_count': ('play_count', {int_or_none}),
            'release_year': ('year', {int_or_none}),
            'artists': ('primary_artists', {lambda x: x.split(', ') if x else None}),
            'webpage_url': ('perma_url', {url_or_none}),
        })
        if webpage_url := info.get('webpage_url') or url:
            info['display_id'] = url_basename(webpage_url)
            info['_old_archive_ids'] = [make_archive_id(JioSaavnSongIE, info['display_id'])]

        return info

    def _call_api(self, type_, token, note='API', params={}):
        return self._download_json(
            self._API_URL, token, f'Downloading {note} JSON', f'Unable to download {note} JSON',
            query={
                '__call': 'webapi.get',
                '_format': 'json',
                '_marker': '0',
                'ctx': 'web6dot0',
                'token': token,
                'type': type_,
                **params,
            })

    def _yield_songs(self, playlist_data):
        for song_data in traverse_obj(playlist_data, ('songs', lambda _, v: v['id'] and v['perma_url'])):
            song_info = self._extract_song(song_data)
            url = smuggle_url(song_info['webpage_url'], {
                'id': song_data['id'],
                'encrypted_media_url': song_data['encrypted_media_url'],
            })
            yield self.url_result(url, JioSaavnSongIE, url_transparent=True, **song_info)


class JioSaavnSongIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:song'
    _VALID_URL = r'https?://(?:www\.)?(?:jiosaavn\.com/song/[^/?#]+/|saavn\.com/s/song/(?:[^/?#]+/){3})(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/song/leja-re/OQsEfQFVUXk',
        'md5': '3b84396d15ed9e083c3106f1fa589c04',
        'info_dict': {
            'id': 'IcoLuefJ',
            'display_id': 'OQsEfQFVUXk',
            'ext': 'm4a',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': r're:https?://c.saavncdn.com/258/Leja-Re-Hindi-2018-20181124024539-500x500.jpg',
            'duration': 205,
            'view_count': int,
            'release_year': 2018,
            'artists': ['Sandesh Shandilya', 'Dhvani Bhanushali', 'Tanishk Bagchi'],
            '_old_archive_ids': ['jiosaavnsong OQsEfQFVUXk'],
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)
        song_data = traverse_obj(smuggled_data, ({
            'id': ('id', {str}),
            'encrypted_media_url': ('encrypted_media_url', {str}),
        }))

        if 'id' in song_data and 'encrypted_media_url' in song_data:
            result = {'id': song_data['id']}
        else:
            # only extract metadata if this is not a url_transparent result
            song_data = self._call_api('song', self._match_id(url))['songs'][0]
            result = self._extract_song(song_data, url)

        result['formats'] = list(self._extract_formats(song_data))
        return result


class JioSaavnAlbumIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:album'
    _VALID_URL = r'https?://(?:www\.)?(?:jio)?saavn\.com/album/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/album/96/buIOjYZDrNA_',
        'info_dict': {
            'id': 'buIOjYZDrNA_',
            'title': '96',
        },
        'playlist_count': 10,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        album_data = self._call_api('album', display_id)

        return self.playlist_result(
            self._yield_songs(album_data), display_id, traverse_obj(album_data, ('title', {str})))


class JioSaavnPlaylistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:playlist'
    _VALID_URL = r'https?://(?:www\.)?(?:jio)?saavn\.com/(?:s/playlist/(?:[^/?#]+/){2}|featured/[^/?#]+/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/s/playlist/2279fbe391defa793ad7076929a2f5c9/mood-english/LlJ8ZWT1ibN5084vKHRj2Q__',
        'info_dict': {
            'id': 'LlJ8ZWT1ibN5084vKHRj2Q__',
            'title': 'Mood English',
        },
        'playlist_mincount': 301,
    }, {
        'url': 'https://www.jiosaavn.com/s/playlist/2279fbe391defa793ad7076929a2f5c9/mood-hindi/DVR,pFUOwyXqIp77B1JF,A__',
        'info_dict': {
            'id': 'DVR,pFUOwyXqIp77B1JF,A__',
            'title': 'Mood Hindi',
        },
        'playlist_mincount': 801,
    }, {
        'url': 'https://www.jiosaavn.com/featured/taaza-tunes/Me5RridRfDk_',
        'info_dict': {
            'id': 'Me5RridRfDk_',
            'title': 'Taaza Tunes',
        },
        'playlist_mincount': 301,
    }]
    _PAGE_SIZE = 50

    def _fetch_page(self, token, page):
        return self._call_api(
            'playlist', token, f'playlist page {page}', {'p': page, 'n': self._PAGE_SIZE})

    def _entries(self, token, first_page_data, page):
        page_data = first_page_data if not page else self._fetch_page(token, page + 1)
        yield from self._yield_songs(page_data)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        playlist_data = self._fetch_page(display_id, 1)
        total_pages = math.ceil(int(playlist_data['list_count']) / self._PAGE_SIZE)

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, display_id, playlist_data),
            total_pages, self._PAGE_SIZE), display_id, traverse_obj(playlist_data, ('listname', {str})))
