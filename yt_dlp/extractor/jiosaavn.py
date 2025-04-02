import functools
import math
import re

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    ISO639Utils,
    OnDemandPagedList,
    clean_html,
    int_or_none,
    make_archive_id,
    smuggle_url,
    unified_strdate,
    unified_timestamp,
    unsmuggle_url,
    url_basename,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class JioSaavnBaseIE(InfoExtractor):
    _URL_BASE_RE = r'https?://(?:www\.)?(?:jio)?saavn\.com'
    _BASE_URL = 'https://www.jiosaavn.com'
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
            'title': (None, ('song', 'title')),
            'album': ('album', {clean_html}),
            'thumbnail': ('image', {url_or_none}, {lambda x: re.sub(r'-\d+x\d+\.', '-500x500.', x)}),
            'description': ('more_info', 'description', {str}),
            'duration': (None, ('duration', ('more_info', 'duration')), {int_or_none}),
            'release_year': ('year', {int_or_none}),
            'timestamp': ('more_info', 'release_time', {unified_timestamp}),
            'upload_date': ('release_date', {unified_strdate}),
            'view_count': ('play_count', {int_or_none}),
            'channel': (None, ('label', ('more_info', 'label')), {str}),
            'channel_id': (None, ('label_id', ('more_info', 'label_id')), {str}),
            'channel_url': (None, ('label_url', ('more_info', 'label_url')), {lambda x: f'{self._BASE_URL}{x}' if x else None}),
            'series': ('more_info', 'show_title', {str}),
            'series_id': ('more_info', 'show_id', {str}),
            'season': ('more_info', 'season_title', {str}),
            'season_number': ('more_info', 'season_no', {int_or_none}),
            'season_id': ('more_info', 'season_id', {str}),
            'episode_number': ('more_info', 'episode_number', {int_or_none}),
            'artists': ('primary_artists', {lambda x: x.split(', ') if x else None}),
            'webpage_url': ('perma_url', {url_or_none}),
            'language': ('language', {lambda x: ISO639Utils.short2long(x.casefold()) or 'und'}),
            'media_type': ('type', {lambda x: x or 'song'}),
            'cast': ('starring', {lambda x: x.split(', ') if x else None}),
        }, get_all=False)
        if webpage_url := info.get('webpage_url') or url:
            info['display_id'] = url_basename(webpage_url)
            info['_old_archive_ids'] = [make_archive_id(JioSaavnSongIE, info['display_id'])]

        if song_data.get('featured_artists'):
            info['artists'].extend(song_data.get('featured_artists').split(', '))

        if not info.get('artists'):
            primary_artists = traverse_obj(song_data, ('more_info', 'artistMap', 'primary_artists', ..., 'name'))
            if primary_artists:
                info['artists'] = primary_artists

        if info.get('artists'):
            info['artists'] = list(set(info['artists']))

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
    _VALID_URL = [
        JioSaavnBaseIE._URL_BASE_RE + r'/shows/[^/?#]+/(?P<id>[^/?#]+)(?:#__youtubedl_smuggle=[^/?#]+)?$',
        JioSaavnBaseIE._URL_BASE_RE + r'/song/[^/?#]+/(?P<id>[^/?#]+)',
        JioSaavnBaseIE._URL_BASE_RE + r'/s/song/(?:[^/?#]+/){3}(?P<id>[^/?#]+)',
    ]
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/song/leja-re/OQsEfQFVUXk',
        'md5': '3b84396d15ed9e083c3106f1fa589c04',
        'info_dict': {
            'id': 'IcoLuefJ',
            'display_id': 'OQsEfQFVUXk',
            'ext': 'm4a',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 205,
            'view_count': int,
            'release_year': 2018,
            'artists': 'count:3',
            '_old_archive_ids': ['jiosaavnsong OQsEfQFVUXk'],
            'media_type': 'song',
            'channel': 'T-Series',
            'language': 'hin',
            'channel_id': '34297',
            'channel_url': 'https://www.jiosaavn.com/label/t-series-albums/6DLuXO3VoTo_',
            'upload_date': '20181124',
        },
    }, {
        'url': 'https://www.jiosaavn.com/song/chuttamalle/P1FfWjZkQ0Q',
        'md5': '96296c58d6ce488a417ef0728fd2d680',
        'info_dict': {
            'id': 'O94kBTtw',
            'display_id': 'P1FfWjZkQ0Q',
            'ext': 'm4a',
            'title': 'Chuttamalle',
            'album': 'Devara Part 1 - Telugu',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 222,
            'view_count': int,
            'release_year': 2024,
            'artists': 'count:3',
            '_old_archive_ids': ['jiosaavnsong P1FfWjZkQ0Q'],
            'media_type': 'song',
            'channel': 'T-Series',
            'language': 'tel',
            'channel_id': '34297',
            'channel_url': 'https://www.jiosaavn.com/label/t-series-albums/6DLuXO3VoTo_',
            'upload_date': '20240926',
        },
    }, {
        'url': 'https://www.jiosaavn.com/shows/non-food-ways-to-boost-your-energy/XFMcKICOCgc_',
        'md5': '0733cd254cfe74ef88bea1eaedcf1f4f',
        'info_dict': {
            'id': 'qqzh3RKZ',
            'display_id': 'XFMcKICOCgc_',
            'ext': 'mp3',
            'title': 'Non-Food Ways To Boost Your Energy',
            'description': 'md5:26e7129644b5c6aada32b8851c3997c8',
            'episode': 'Episode 1',
            'timestamp': 1640563200,
            'series': 'Holistic Lifestyle With Neha Ranglani',
            'series_id': '52397',
            'season': 'Holistic Lifestyle With Neha Ranglani',
            'season_number': 1,
            'season_id': '61273',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 311,
            'view_count': int,
            'release_year': 2021,
            '_old_archive_ids': ['jiosaavnsong XFMcKICOCgc_'],
            'media_type': 'episode',
            'language': 'eng',
            'channel': 'Saavn OG',
            'channel_id': '1953876',
            'episode_number': 1,
            'upload_date': '20211227',
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }, {
        'url': 'https://www.jiosaavn.com/shows/himesh-reshammiya/Kr8fmfSN4vo_',
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
            video_id = self._match_id(url)
            if 'shows' in url:
                song_data = self._call_api('episode', video_id)['episodes'][0]
            else:
                song_data = self._call_api('song', video_id)['songs'][0]
            if not song_data.get('encrypted_media_url'):
                song_data['encrypted_media_url'] = song_data['more_info']['encrypted_media_url']
            result = self._extract_song(song_data, url)

        result['formats'] = list(self._extract_formats(song_data))
        return result


class JioSaavnAlbumIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:album'
    _VALID_URL = rf'{JioSaavnBaseIE._URL_BASE_RE}/album/[^/?#]+/(?P<id>[^/?#]+)'
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
        album_title = traverse_obj(album_data, ('title', {str}))
        return self.playlist_result(self._yield_songs(album_data), display_id, album_title)


class JioSaavnPlaylistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:playlist'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/(?:s/playlist/(?:[^/?#]+/){2}|featured/[^/?#]+/)(?P<id>[^/?#]+)'
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
        'playlist_mincount': 750,
    }, {
        'url': 'https://www.jiosaavn.com/featured/taaza-tunes/Me5RridRfDk_',
        'info_dict': {
            'id': 'Me5RridRfDk_',
            'title': 'Taaza Tunes',
        },
        'playlist_mincount': 50,
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


class JioSaavnShowPlaylistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:showplaylist'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/shows/[^#/?]+/(?P<season>\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/shows/talking-music/1/PjReFP-Sguk_',
        'info_dict': {
            'id': 'PjReFP-Sguk_-1',
            'title': 'Talking Music',
        },
        'playlist_mincount': 10,
    }]
    _PAGE_SIZE = 10

    def _fetch_page(self, token, season_id, page):
        return self._call_api('show', token, f'show page {page}', {
            'p': page, '__call': 'show.getAllEpisodes', 'show_id': token, 'season_number': season_id,
            'api_version': '4', 'sort_order': 'desc'})

    def _yield_songs(self, playlist_data):
        for song_data in playlist_data:
            song_info = self._extract_song(song_data)
            url = smuggle_url(song_info['webpage_url'], {
                'id': song_data['id'],
                'encrypted_media_url': song_data['more_info']['encrypted_media_url'],
            })
            yield self.url_result(url, JioSaavnSongIE, url_transparent=True, **song_info)

    def _entries(self, show_id, season_id, page):
        page_data = self._fetch_page(show_id, season_id, page + 1)
        yield from self._yield_songs(page_data)

    def _real_extract(self, url):
        season_id, show_id = self._match_valid_url(url).groups()
        playlist_id = f'{show_id}-{season_id}'
        webpage = self._download_webpage(url, playlist_id)
        webpage = webpage.replace('undefined', 'null')
        json_data = self._search_json(r'"showView"\s*:\s*', webpage, 'jdata', playlist_id)
        token = traverse_obj(json_data, 'current_id')
        show_title = traverse_obj(json_data, ('show', 'title', 'text', {str}))
        entries = OnDemandPagedList(functools.partial(self._entries, token, season_id), self._PAGE_SIZE)
        return self.playlist_result(entries, playlist_id, show_title)


class JioSaavnArtistIE(JioSaavnShowPlaylistIE):
    IE_NAME = 'jiosaavn:artist'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/artist/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/artist/krsna-songs/rYLBEve2z3U_',
        'info_dict': {
            'id': 'rYLBEve2z3U_',
            'title': 'KR$NA',
        },
        'playlist_mincount': 99,
    }, {
        'url': 'https://www.jiosaavn.com/artist/sanam-puri-songs/SkNEv3qRhDE_',
        'info_dict': {
            'id': 'SkNEv3qRhDE_',
            'title': 'Sanam Puri',
        },
        'playlist_mincount': 55,
    }]
    _PAGE_SIZE = 50

    def _fetch_page(self, token, page):
        return self._call_api('artist', token, f'artist page {page + 1}', {
            'p': page, 'n_song': self._PAGE_SIZE, 'n_album': self._PAGE_SIZE, 'sub_type': '',
            'includeMetaTags': '', 'api_version': '4', 'category': 'alphabetical', 'sort_order': 'asc'})

    def _entries(self, token, page):
        page_data = self._first_page if page == 0 else self._fetch_page(token, page)
        playlist_data = page_data.get('topSongs')
        yield from self._yield_songs(playlist_data)

    def _generate_result(self, token):
        # note:
        # 1. the total number of songs in a page result is not constant
        # 2. end of list is identified by 'topSongs' array being empty
        page = 0
        result = []

        # added static page count limit to avoid potential infinite loop
        while page < 20000:
            entries = list(self._entries(token, page))
            if len(entries) == 0:
                break
            result.extend(entries)
            page += 1
        return result

    def _real_extract(self, url):
        display_id = self._match_id(url)
        self._first_page = self._fetch_page(display_id, 0)
        entries = self._generate_result(display_id)
        name = self._first_page.get('name')

        return self.playlist_result(entries, display_id, name)
