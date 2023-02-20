from .common import InfoExtractor
from ..utils import (
    str_to_int,
    unified_strdate,
)


class RJApiBaseExtractor(InfoExtractor):
    RJ_API_TOKEN = None
    RJ_BUILD_ID = None
    RJ_VERSION = None
    RJ_USER_AGENT = None
    RJ_API_HEADERS = None

    def _rj_ensure_vars(self):
        index_page = None
        app_js = None
        if self.RJ_BUILD_ID is None:
            index_page = self._download_webpage('https://play.radiojavan.com/', 'index')
            self.RJ_BUILD_ID = self._html_search_regex(r'"buildId":"([^"]+?)"', index_page, 'Build ID', 'ec895e263b57af451279537938786c42071d0105')

        if self.RJ_API_TOKEN is None or self.RJ_VERSION:
            index_page = index_page if index_page is not None else self._download_webpage('https://play.radiojavan.com/', 'index')
            js_app_hash = self._html_search_regex(r'https://play\.radiojavan\.com/_next/static/chunks/pages/_app-([^"]+?)"', index_page, "JS App hash", fatal=True)
            js_app_url = f'https://play.radiojavan.com/_next/static/chunks/pages/_app-{js_app_hash}'
            app_js = self._download_webpage(js_app_url, 'JS App URL')
            self.RJ_API_TOKEN = self._search_regex(r'\["x-api-key"\]="([^"]+?)"', app_js, 'Api Token', '40e87948bd4ef75efe61205ac5f468a9fd2b970511acf58c49706ecb984f1d67')
            self.RJ_VERSION = self._search_regex(r'"Radio Javan/"\.concat\("([^"]+?)"', app_js, 'RJ Version', '4.0.2')

        if self.RJ_API_HEADERS is None:
            self.RJ_USER_AGENT = f'Radio Javan/{self.RJ_VERSION}/{self.RJ_BUILD_ID} (Windows 10 64-bit 97.0.4692.71) com.radioJavan.rj.desktop'
            self.RJ_API_HEADERS = {
                'x-rj-user-agent': self.RJ_USER_AGENT,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
                'x-api-key': self.RJ_API_TOKEN,
                'referer': 'https://play.radiojavan.com/',
            }


RJ_API_BASE_EXTRACTOR = RJApiBaseExtractor()


def _init_rj_api_base(downloader):
    RJ_API_BASE_EXTRACTOR.set_downloader(downloader)
    RJ_API_BASE_EXTRACTOR._rj_ensure_vars()


class RadioJavanPodcastShowIE(InfoExtractor):
    _VALID_URL = r'https?://play\.radiojavan\.com/(podcast/show/(?P<slug>[^/]+)/?|podcast/show\?id=(?P<id>[^&]+).*)'
    IE_NAME = 'radiojavan:playlist:podcasts'
    _TEST = {
        'url': 'https://play.radiojavan.com/podcast/show/Abo-Atash',
        'info_dict': {
            'id': 'Abo-Atash',
            'title': 'Abo Atash',
        },
        'playlist_mincount': 5,
    }

    def _real_extract(self, url):
        podcast_show_id, podcast_show_slug = self._match_valid_url(url).group('id', 'slug')

        podcast_show_json = {}
        if podcast_show_id is None:
            webpage = self._download_webpage(f'https://play.radiojavan.com/podcast/show/{podcast_show_slug.lower()}', podcast_show_slug)
            podcast_show_json = self._parse_json(self._html_search_regex(r'"pageProps":{"show":([\s\S]*?)}},"page"', webpage, 'Podcast Show JSON'), podcast_show_slug)
            podcast_show_id = podcast_show_json.get('id')
        else:
            _init_rj_api_base(self._downloader)
            podcast_show_json = self._download_json(f'https://play.radiojavan.com/api/p/podcast_show?id={podcast_show_id}', podcast_show_id, headers=RJ_API_BASE_EXTRACTOR.RJ_API_HEADERS)
            podcast_show_slug = podcast_show_json.get('permlink')

        playlist_items = [
            self.url_result(url='https://play.radiojavan.com/podcast?id=' + str(podcast.get('id')),
                            video_title=podcast.get("title"),
                            video_id=podcast.get('permlink'),
                            url_transparent=False)
            for podcast in podcast_show_json.get('podcasts')
        ]

        return self.playlist_result(entries=playlist_items, playlist_id=podcast_show_slug, playlist_title=podcast_show_json.get('title'), multi_video=False)


class RadioJavanPlaylistMp3IE(InfoExtractor):
    _VALID_URL = r'https?://play\.radiojavan\.com/playlist/mp3/(?P<id>[^/]+)/?'
    IE_NAME = 'radiojavan:playlist:mp3'
    _TEST = {
        'url': 'https://play.radiojavan.com/playlist/mp3/6449cdabd351',
        'info_dict': {
            'id': '6449cdabd351',
            'title': 'Top Songs Pop',
        },
        'playlist_mincount': 5,
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        playlist_json = {}
        webpage = self._download_webpage(f'https://play.radiojavan.com/playlist/mp3/{playlist_id.lower()}', playlist_id)
        playlist_json = self._parse_json(self._html_search_regex(r'id="schema:music-playlist" type="application/ld\+json"[^>]+?>([\s\S]*?)</script>', webpage, 'Playlist JSON'), playlist_id)
        if playlist_json is None or playlist_json == {}:
            _init_rj_api_base(self._downloader)
            playlist_json = self._download_json(f'https://play.radiojavan.com/api/p/mp3_playlist_with_items?id={playlist_id}', playlist_id, headers=RJ_API_BASE_EXTRACTOR.RJ_API_HEADERS)

        playlist_items = [self.url_result(url=playlist_track.get('url'), video_title=playlist_track.get('name'), url_transparent=False) for playlist_track in playlist_json.get('track')]

        return self.playlist_result(entries=playlist_items, playlist_id=playlist_id, playlist_title=playlist_json.get('name'), multi_video=False)


class RadioJavanPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://play\.radiojavan\.com/(podcast/(?P<slug>[^/]+)/?$|podcast\?id=(?P<id>[^&]+).*)'
    IE_NAME = 'radiojavan:podcast'
    _TEST = {
        'url': 'https://play.radiojavan.com/podcast/Abo-Atash-118',
        'md5': 'c74b6a5adbd99c4b38a0f266dd6fdf4a',
        'info_dict': {
            'id': 'Abo-Atash-118',
            'ext': 'mp3',
            'title': 'DJ Taba - Abo Atash 118',
            'alt_title': 'Abo Atash 118 Podcast by DJ Taba',
            'track': 'Abo Atash 118',
            'artist': 'DJ Taba',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20210126',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'explicit': False,
        }
    }

    def _real_extract(self, url):
        podcast_id, podcast_slug = self._match_valid_url(url).group('id', 'slug')

        podcast_json = {}
        if podcast_id is None:
            webpage = self._download_webpage(f'https://play.radiojavan.com/podcast/{podcast_slug.lower()}', podcast_slug)
            podcast_json = self._parse_json(self._html_search_regex(r'"pageProps":{"media":([\s\S]*?)}},"page"', webpage, 'Podcast JSON'), podcast_slug)
            podcast_id = podcast_json.get('id')
        else:
            _init_rj_api_base(self._downloader)
            podcast_json = self._download_json(f'https://play.radiojavan.com/api/p/podcast?id={podcast_id}', podcast_id, headers=RJ_API_BASE_EXTRACTOR.RJ_API_HEADERS)
            podcast_slug = podcast_json.get('permlink')

        artist = podcast_json.get('podcast_artist')
        song = podcast_json.get('title')

        formats = [
            {'url': podcast_json.get('link'), 'quality': 1}
        ]

        formats.extend(self._extract_m3u8_formats(
            podcast_json.get('hls_link'), podcast_slug, 'm4a', 'm3u8_native', m3u8_id='hls',
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information'))

        return {
            'id': podcast_slug,
            'title': f'{artist} - {song}',
            'alt_title': f'{song} Podcast by {artist}',
            'track': song,
            'artist': artist,
            'formats': formats,
            'thumbnail': podcast_json.get('photo_large'),
            'upload_date': unified_strdate(podcast_json.get('created_at')),
            'view_count': str_to_int(podcast_json.get('plays')),
            'like_count': str_to_int(podcast_json.get('likes')),
            'dislike_count': str_to_int(podcast_json.get('dislikes')),
            'explicit': podcast_json.get('explicit'),
        }


class RadioJavanMp3IE(InfoExtractor):
    _VALID_URL = r'https?://play\.radiojavan\.com/(song/(?P<slug>[^/]+)/?|song\?id=(?P<id>[^&]+).*)'
    IE_NAME = 'radiojavan:mp3'
    _TESTS = [{
        'url': 'https://play.radiojavan.com/song/Ell3-Baroon',
        'md5': 'cb877362f8e8fabb1aad6e2f1bf1bf97',
        'info_dict': {
            'id': 'Ell3-Baroon',
            'ext': 'mp3',
            'title': 'Ell3 - Baroon',
            'alt_title': 'ال - بارون',
            'track': 'Baroon',
            'artist': 'Ell3',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20221226',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'explicit': False,
        }
    },
        {
        'url': 'https://play.radiojavan.com/song?id=110685',
        'md5': 'cb877362f8e8fabb1aad6e2f1bf1bf97',
        'info_dict': {
            'id': 'Ell3-Baroon',
            'ext': 'mp3',
            'title': 'Ell3 - Baroon',
            'alt_title': 'ال - بارون',
            'track': 'Baroon',
            'artist': 'Ell3',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20221226',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'explicit': False,
        }
    }]

    def _real_extract(self, url):
        mp3_id, mp3_slug = self._match_valid_url(url).group('id', 'slug')

        mp3_json = {}
        if mp3_id is None:
            webpage = self._download_webpage(f'https://play.radiojavan.com/song/{mp3_slug.lower()}', mp3_slug)
            mp3_json = self._parse_json(self._html_search_regex(r'"pageProps":{"media":([\s\S]*?)}},"page"', webpage, 'Mp3 JSON'), mp3_slug)
            mp3_id = mp3_json.get('id')
        else:
            _init_rj_api_base(self._downloader)
            mp3_json = self._download_json(f'https://play.radiojavan.com/api/p/mp3?id={mp3_id}', mp3_id, headers=RJ_API_BASE_EXTRACTOR.RJ_API_HEADERS)
            mp3_slug = mp3_json.get('permlink')

        artist = mp3_json.get('artist')
        song = mp3_json.get('song')

        artist_farsi = mp3_json.get('artist_farsi') or artist
        song_farsi = mp3_json.get('song_farsi') or song

        formats = [
            {'url': mp3_json.get('link'), 'quality': 1}
        ]

        formats.extend(self._extract_m3u8_formats(
            mp3_json.get('hls_link'), mp3_json, 'm4a', 'm3u8_native', m3u8_id='hls',
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information'))

        return {
            'id': mp3_slug,
            'title': f'{artist} - {song}',
            'alt_title': f'{artist_farsi} - {song_farsi}',
            'track': song,
            'artist': artist,
            'formats': formats,
            'thumbnail': mp3_json.get('photo'),
            'upload_date': unified_strdate(mp3_json.get('created_at')),
            'view_count': str_to_int(mp3_json.get('plays')),
            'like_count': str_to_int(mp3_json.get('likes')),
            'dislike_count': str_to_int(mp3_json.get('dislikes')),
            'explicit': mp3_json.get('explicit'),
        }


class RadioJavanIE(InfoExtractor):
    _VALID_URL = r'https?://play\.radiojavan\.com/(video/(?P<slug>[^/]+)/?|video\?id=(?P<id>[^&]+).*)'
    IE_NAME = 'radiojavan:video'
    _TEST = {
        'url': 'https://play.radiojavan.com/video/chaartaar-ashoobam',
        'md5': 'e85208ffa3ca8b83534fca9fe19af95b',
        'info_dict': {
            'id': 'chaartaar-ashoobam',
            'ext': 'mp4',
            'title': 'Chaartaar - Ashoobam',
            'alt_title': 'چارتار - آشوبم',
            'cast': ['Chaartaar'],
            'track': 'Ashoobam',
            'artist': 'Chaartaar',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20150215',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'explicit': False,
        }
    }

    def _real_extract(self, url):
        video_id, video_slug = self._match_valid_url(url).group('id', 'slug')

        video_json = {}
        if video_id is None:
            webpage = self._download_webpage(f'https://play.radiojavan.com/video/{video_slug.lower()}', video_slug)
            video_json = self._parse_json(self._html_search_regex(r'"pageProps":{"media":([\s\S]*?)}},"page"', webpage, 'Video JSON'), video_slug)
            video_id = video_json.get('id')
        else:
            _init_rj_api_base(self._downloader)
            video_json = self._download_json(f'https://play.radiojavan.com/api/p/video?id={video_id}', video_id, headers=RJ_API_BASE_EXTRACTOR.RJ_API_HEADERS)
            video_slug = video_json.get('permlink')

        formats = [
            {'url': video_json.get('hq_link'), 'quality': 2},
            {'url': video_json.get('lq_link'), 'quality': 1},
        ]

        formats.extend(self._extract_m3u8_formats(
            video_json.get('hls'), video_id, None, 'm3u8_native', m3u8_id='hls',
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information'))

        artist = video_json.get('artist')
        song = video_json.get('song')

        artist_farsi = video_json.get('artist_farsi') or artist
        song_farsi = video_json.get('song_farsi') or song

        return {
            'id': video_slug,
            'title': f'{artist} - {song}',
            'alt_title': f'{artist_farsi} - {song_farsi}',
            'cast': [artist],
            'track': song,
            'artist': artist,
            'thumbnail': video_json.get('photo_large'),
            'upload_date': unified_strdate(video_json.get('created_at')),
            'view_count': str_to_int(video_json.get('views')),
            'like_count': str_to_int(video_json.get('likes')),
            'dislike_count': str_to_int(video_json.get('dislikes')),
            'explicit': video_json.get('explicit'),
            'formats': formats,
        }
