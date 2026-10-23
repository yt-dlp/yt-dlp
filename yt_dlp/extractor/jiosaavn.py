import functools
import itertools
import math
import re

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    ISO639Utils,
    OnDemandPagedList,
    clean_html,
    int_or_none,
    js_to_json,
    make_archive_id,
    orderedSet,
    smuggle_url,
    unified_strdate,
    unified_timestamp,
    unsmuggle_url,
    url_basename,
    url_or_none,
    urlencode_postdata,
    urljoin,
    variadic,
)
from ..utils.traversal import traverse_obj


class JioSaavnBaseIE(InfoExtractor):
    _URL_BASE_RE = r'https?://(?:www\.)?(?:jio)?saavn\.com'
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

    def _extract_formats(self, item_data):
        # Show/episode JSON data has a slightly different structure than song JSON data
        if media_url := traverse_obj(item_data, ('more_info', 'encrypted_media_url', {str})):
            item_data.setdefault('encrypted_media_url', media_url)

        for bitrate in self.requested_bitrates:
            media_data = self._download_json(
                self._API_URL, item_data['id'],
                f'Downloading format info for {bitrate}',
                fatal=False, data=urlencode_postdata({
                    '__call': 'song.generateAuthToken',
                    '_format': 'json',
                    'bitrate': bitrate,
                    'url': item_data['encrypted_media_url'],
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

    @staticmethod
    def _extract_song(song_data, url=None):
        info = traverse_obj(song_data, {
            'id': ('id', {str}),
            'title': (('song', 'title'), {clean_html}, any),
            'album': ((None, 'more_info'), 'album', {clean_html}, any),
            'duration': ((None, 'more_info'), 'duration', {int_or_none}, any),
            'channel': ((None, 'more_info'), 'label', {str}, any),
            'channel_id': ((None, 'more_info'), 'label_id', {str}, any),
            'channel_url': ((None, 'more_info'), 'label_url', {urljoin('https://www.jiosaavn.com/')}, any),
            'release_date': ((None, 'more_info'), 'release_date', {unified_strdate}, any),
            'release_year': ('year', {int_or_none}),
            'thumbnail': ('image', {url_or_none}, {lambda x: re.sub(r'-\d+x\d+\.', '-500x500.', x)}),
            'view_count': ('play_count', {int_or_none}),
            'language': ('language', {lambda x: ISO639Utils.short2long(x.casefold()) or 'und'}),
            'webpage_url': ('perma_url', {url_or_none}),
            'artists': ('more_info', 'artistMap', 'primary_artists', ..., 'name', {str}, filter, all),
        })
        if webpage_url := info.get('webpage_url') or url:
            info['display_id'] = url_basename(webpage_url)
            info['_old_archive_ids'] = [make_archive_id(JioSaavnSongIE, info['display_id'])]

        if primary_artists := traverse_obj(song_data, ('primary_artists', {lambda x: x.split(', ') if x else None})):
            info['artists'].extend(primary_artists)
        if featured_artists := traverse_obj(song_data, ('featured_artists', {str}, filter)):
            info['artists'].extend(featured_artists.split(', '))
        info['artists'] = orderedSet(info['artists']) or None

        return info

    @staticmethod
    def _extract_episode(episode_data, url=None):
        info = JioSaavnBaseIE._extract_song(episode_data, url)
        info.pop('_old_archive_ids', None)
        info.update(traverse_obj(episode_data, {
            'description': ('more_info', 'description', {str}),
            'timestamp': ('more_info', 'release_time', {unified_timestamp}),
            'series': ('more_info', 'show_title', {str}),
            'series_id': ('more_info', 'show_id', {str}),
            'season': ('more_info', 'season_title', {str}),
            'season_number': ('more_info', 'season_no', {int_or_none}),
            'season_id': ('more_info', 'season_id', {str}),
            'episode_number': ('more_info', 'episode_number', {int_or_none}),
            'cast': ('starring', {lambda x: x.split(', ') if x else None}),
        }))
        return info

    def _extract_jiosaavn_result(self, url, endpoint, response_key, parse_func):
        url, smuggled_data = unsmuggle_url(url)
        data = traverse_obj(smuggled_data, ({
            'id': ('id', {str}),
            'encrypted_media_url': ('encrypted_media_url', {str}),
        }))

        if 'id' in data and 'encrypted_media_url' in data:
            result = {'id': data['id']}
        else:
            # only extract metadata if this is not a url_transparent result
            data = self._call_api(endpoint, self._match_id(url))[response_key][0]
            result = parse_func(data, url)

        result['formats'] = list(self._extract_formats(data))
        return result

    def _yield_items(self, playlist_data, keys=None, parse_func=None):
        """Subclasses using this method must set _ENTRY_IE"""
        if parse_func is None:
            parse_func = self._extract_song

        for item_data in traverse_obj(playlist_data, (
            *variadic(keys, (str, bytes, dict, set)), lambda _, v: v['id'] and v['perma_url'],
        )):
            info = parse_func(item_data)
            url = smuggle_url(info['webpage_url'], traverse_obj(item_data, {
                'id': ('id', {str}),
                'encrypted_media_url': ((None, 'more_info'), 'encrypted_media_url', {str}, any),
            }))
            yield self.url_result(url, self._ENTRY_IE, url_transparent=True, **info)


class JioSaavnSongIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:song'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'(?:/song/[^/?#]+/|/s/song/(?:[^/?#]+/){3})(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/song/leja-re/OQsEfQFVUXk',
        'md5': '3b84396d15ed9e083c3106f1fa589c04',
        'info_dict': {
            'id': 'IcoLuefJ',
            'display_id': 'OQsEfQFVUXk',
            'ext': 'm4a',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 205,
            'view_count': int,
            'release_year': 2018,
            'artists': ['Sandesh Shandilya', 'Dhvani Bhanushali', 'Tanishk Bagchi'],
            '_old_archive_ids': ['jiosaavnsong OQsEfQFVUXk'],
            'channel': 'T-Series',
            'language': 'hin',
            'channel_id': '34297',
            'channel_url': 'https://www.jiosaavn.com/label/t-series-albums/6DLuXO3VoTo_',
            'release_date': '20181124',
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
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 222,
            'view_count': int,
            'release_year': 2024,
            'artists': 'count:3',
            '_old_archive_ids': ['jiosaavnsong P1FfWjZkQ0Q'],
            'channel': 'T-Series',
            'language': 'tel',
            'channel_id': '34297',
            'channel_url': 'https://www.jiosaavn.com/label/t-series-albums/6DLuXO3VoTo_',
            'release_date': '20240926',
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_jiosaavn_result(url, 'song', 'songs', self._extract_song)


class JioSaavnShowIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:show'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/shows/[^/?#]+/(?P<id>[^/?#]{11,})/?(?:$|[?#])'
    _TESTS = [{
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
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 311,
            'view_count': int,
            'release_year': 2021,
            'language': 'eng',
            'channel': 'Saavn OG',
            'channel_id': '1953876',
            'episode_number': 1,
            'upload_date': '20211227',
            'release_date': '20211227',
        },
    }, {
        'url': 'https://www.jiosaavn.com/shows/himesh-reshammiya/Kr8fmfSN4vo_',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_jiosaavn_result(url, 'episode', 'episodes', self._extract_episode)


class JioSaavnAlbumIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:album'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/album/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/album/96/buIOjYZDrNA_',
        'info_dict': {
            'id': 'buIOjYZDrNA_',
            'title': '96',
        },
        'playlist_count': 10,
    }]
    _ENTRY_IE = JioSaavnSongIE

    def _real_extract(self, url):
        display_id = self._match_id(url)
        album_data = self._call_api('album', display_id)

        return self.playlist_result(
            self._yield_items(album_data, 'songs'), display_id, traverse_obj(album_data, ('title', {str})))


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
    _ENTRY_IE = JioSaavnSongIE
    _PAGE_SIZE = 50

    def _fetch_page(self, token, page):
        return self._call_api(
            'playlist', token, f'playlist page {page}', {'p': page, 'n': self._PAGE_SIZE})

    def _entries(self, token, first_page_data, page):
        page_data = first_page_data if not page else self._fetch_page(token, page + 1)
        yield from self._yield_items(page_data, 'songs')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        playlist_data = self._fetch_page(display_id, 1)
        total_pages = math.ceil(int(playlist_data['list_count']) / self._PAGE_SIZE)

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, display_id, playlist_data),
            total_pages, self._PAGE_SIZE), display_id, traverse_obj(playlist_data, ('listname', {str})))


class JioSaavnShowPlaylistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:show:playlist'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/shows/(?P<show>[^#/?]+)/(?P<season>\d+)/[^/?#]+'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/shows/talking-music/1/PjReFP-Sguk_',
        'info_dict': {
            'id': 'talking-music-1',
            'title': 'Talking Music',
        },
        'playlist_mincount': 11,
    }]
    _ENTRY_IE = JioSaavnShowIE
    _PAGE_SIZE = 10

    def _fetch_page(self, show_id, season_id, page):
        return self._call_api('show', show_id, f'show page {page}', {
            'p': page,
            '__call': 'show.getAllEpisodes',
            'show_id': show_id,
            'season_number': season_id,
            'api_version': '4',
            'sort_order': 'desc',
        })

    def _entries(self, show_id, season_id, page):
        page_data = self._fetch_page(show_id, season_id, page + 1)
        yield from self._yield_items(page_data, keys=None, parse_func=self._extract_episode)

    def _real_extract(self, url):
        show_slug, season_id = self._match_valid_url(url).group('show', 'season')
        playlist_id = f'{show_slug}-{season_id}'
        webpage = self._download_webpage(url, playlist_id)

        show_info = self._search_json(
            r'window\.__INITIAL_DATA__\s*=', webpage, 'initial data',
            playlist_id, transform_source=js_to_json)['showView']
        show_id = show_info['current_id']

        entries = OnDemandPagedList(functools.partial(self._entries, show_id, season_id), self._PAGE_SIZE)
        return self.playlist_result(
            entries, playlist_id, traverse_obj(show_info, ('show', 'title', 'text', {str})))


class JioSaavnArtistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:artist'
    _VALID_URL = JioSaavnBaseIE._URL_BASE_RE + r'/artist/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/artist/krsna-songs/rYLBEve2z3U_',
        'info_dict': {
            'id': 'rYLBEve2z3U_',
            'title': 'KR$NA',
        },
        'playlist_mincount': 38,
    }, {
        'url': 'https://www.jiosaavn.com/artist/sanam-puri-songs/SkNEv3qRhDE_',
        'info_dict': {
            'id': 'SkNEv3qRhDE_',
            'title': 'Sanam Puri',
        },
        'playlist_mincount': 51,
    }]
    _ENTRY_IE = JioSaavnSongIE
    _PAGE_SIZE = 50

    def _fetch_page(self, artist_id, page):
        return self._call_api('artist', artist_id, f'artist page {page + 1}', {
            'p': page,
            'n_song': self._PAGE_SIZE,
            'n_album': self._PAGE_SIZE,
            'sub_type': '',
            'includeMetaTags': '',
            'api_version': '4',
            'category': 'alphabetical',
            'sort_order': 'asc',
        })

    def _entries(self, artist_id, first_page):
        for page in itertools.count():
            playlist_data = first_page if not page else self._fetch_page(artist_id, page)
            if not traverse_obj(playlist_data, ('topSongs', ..., {dict})):
                break
            yield from self._yield_items(playlist_data, 'topSongs')

    def _real_extract(self, url):
        artist_id = self._match_id(url)
        first_page = self._fetch_page(artist_id, 0)

        return self.playlist_result(
            self._entries(artist_id, first_page), artist_id,
            traverse_obj(first_page, ('name', {str})))
