from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    traverse_obj,
    try_get,
    urljoin,
)


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-my-girlfriend-is-an-alien-hindi-dubbed/season-1/episode-1-online-9d2013d31d5835bb8400e3b3c5e7bb72',
        'info_dict': {
            'id': '9d2013d31d5835bb8400e3b3c5e7bb72',
            'display_id': 'episode-1-online',
            'ext': 'mp4',
            'title': 'Episode 1',
            'description': 'md5:62ed43eb9fec5efde5cf3bd1040b7670',
            'season_number': 1,
            'episode_number': 1,
            'duration': 2451,
            'season': 'Season 1',
            'series': 'My Girlfriend Is An Alien (Hindi Dubbed)',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-knock-knock-hindi-dubbed-movie-online-b9fa28df3bfb8758874735bbd7d2655a?watch=true',
        'info_dict': {
            'id': 'b9fa28df3bfb8758874735bbd7d2655a',
            'display_id': 'episode-1-online',
            'ext': 'mp4',
            'title': 'Knock Knock (Hindi Dubbed)',
            'description': 'md5:4160f2dfc3b87c524261366f6b736329',
            'duration': 5970,
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        'url': 'https://www.mxplayer.in/show/watch-shaitaan/season-1/the-infamous-taxi-gang-of-meerut-online-45055d5bcff169ad48f2ad7552a83d6c',
        'info_dict': {
            'id': '45055d5bcff169ad48f2ad7552a83d6c',
            'ext': 'mp4',
            'title': 'The infamous taxi gang of Meerut',
            'description': 'md5:033a0a7e3fd147be4fb7e07a01a3dc28',
            'season_number': 1,
            'episode_number': 1,
            'duration': 2332,
            'season': 'Season 1',
            'series': 'Shaitaan',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
        'skip': 'No longer available.'
    }, {
        'url': 'https://www.mxplayer.in/show/watch-aashram/chapter-1/duh-swapna-online-d445579792b0135598ba1bc9088a84cb',
        'info_dict': {
            'id': 'd445579792b0135598ba1bc9088a84cb',
            'display_id': 'duh-swapna-online',
            'ext': 'mp4',
            'title': 'Duh Swapna',
            'description': 'md5:35ff39c4bdac403c53be1e16a04192d8',
            'season_number': 1,
            'episode_number': 3,
            'duration': 2568,
            'season': 'Season 1',
            'series': 'Aashram',
            'episode': 'Episode 3'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-dangerous/season-1/chapter-1-online-5a351b4f9fb69436f6bd6ae3a1a75292',
        'info_dict': {
            'id': '5a351b4f9fb69436f6bd6ae3a1a75292',
            'display_id': 'chapter-1-online',
            'ext': 'mp4',
            'title': 'Chapter 1',
            'description': 'md5:233886b8598bc91648ac098abe1d288f',
            'season_number': 1,
            'episode_number': 1,
            'duration': 1305,
            'season': 'Season 1',
            'series': 'Dangerous',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-the-attacks-of-2611-movie-online-0452f0d80226c398d63ce7e3ea40fa2d',
        'info_dict': {
            'id': '0452f0d80226c398d63ce7e3ea40fa2d',
            'ext': 'mp4',
            'title': 'The Attacks of 26/11',
            'description': 'md5:689bacd29e97b3f31eaf519eb14127e5',
            'duration': 6085,
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
        'skip': 'No longer available. Cannot be played on browser'
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-kitne-door-kitne-paas-movie-online-a9e9c76c566205955f70d8b2cb88a6a2',
        'info_dict': {
            'id': 'a9e9c76c566205955f70d8b2cb88a6a2',
            'display_id': 'watch-kitne-door-kitne-paas-movie-online',
            'title': 'Kitne Door Kitne Paas',
            'duration': 8458,
            'ext': 'mp4',
            'description': 'md5:fb825f3c542513088024dcafef0921b4',
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-ek-thi-begum-hindi/season-2/game-of-power-online-5e5305c28f1409847cdc4520b6ad77cf',
        'info_dict': {
            'id': '5e5305c28f1409847cdc4520b6ad77cf',
            'display_id': 'game-of-power-online',
            'title': 'Game Of Power',
            'duration': 1845,
            'ext': 'mp4',
            'description': 'md5:1d0948d2a5312d7013792d53542407f9',
            'series': 'Ek Thi Begum (Hindi)',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-deewane-huye-paagal-movie-online-4f9175c40a11c3994182a65afdd37ec6?watch=true',
        'info_dict': {
            'id': '4f9175c40a11c3994182a65afdd37ec6',
            'display_id': 'watch-deewane-huye-paagal-movie-online',
            'title': 'Deewane Huye Paagal',
            'duration': 9037,
            'ext': 'mp4',
            'description': 'md5:d17bd5c651016c4ed2e6f8a4ace15534',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_type, display_id, video_id = self._match_valid_url(url).group('type', 'display_id', 'id')
        if 'show' in video_type:
            video_type = 'episode'

        data_json = self._download_json(
            f'https://api.mxplay.com/v1/web/detail/video?type={video_type}&id={video_id}', display_id)

        formats, subtitles = [], {}
        m3u8_url = urljoin('https://llvod.mxplay.com/', traverse_obj(
            data_json, ('stream', (('thirdParty', 'hlsUrl'), ('hls', 'high'))), get_all=False))
        if m3u8_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, display_id, 'mp4', fatal=False)
        mpd_url = urljoin('https://llvod.mxplay.com/', traverse_obj(
            data_json, ('stream', (('thirdParty', 'dashUrl'), ('dash', 'high'))), get_all=False))
        if mpd_url:
            fmts, subs = self._extract_mpd_formats_and_subtitles(mpd_url, display_id, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        season = traverse_obj(data_json, ('container', 'title'))
        return {
            'id': video_id,
            'title': data_json.get('title'),
            'formats': formats,
            'subtitles': subtitles,
            'display_id': display_id,
            'duration': data_json.get('duration'),
            'series': traverse_obj(data_json, ('container', 'container', 'title')),
            'description': data_json.get('description'),
            'season': season,
            'season_number': int_or_none(
                self._search_regex(r'Season (\d+)', season, 'Season Number', default=None)),
            'episode_number': data_json.get('sequence') or None,
        }


class MxplayerShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/show/(?P<display_id>[-\w]+)-(?P<id>\w+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-chakravartin-ashoka-samrat-series-online-a8f44e3cc0814b5601d17772cedf5417',
        'playlist_mincount': 440,
        'info_dict': {
            'id': 'a8f44e3cc0814b5601d17772cedf5417',
            'title': 'Watch Chakravartin Ashoka Samrat Series Online',
        }
    }]

    _API_SHOW_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowseasons?type=tv_show&id={}&device-density=2&platform=com.mxplay.desktop&content-languages=hi,en"
    _API_EPISODES_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowepisodes?type=season&id={}&device-density=1&platform=com.mxplay.desktop&content-languages=hi,en&{}"

    def _entries(self, show_id):
        show_json = self._download_json(
            self._API_SHOW_URL.format(show_id),
            video_id=show_id, headers={'Referer': 'https://mxplayer.in'})
        page_num = 0
        for season in show_json.get('items') or []:
            season_id = try_get(season, lambda x: x['id'], compat_str)
            next_url = ''
            while next_url is not None:
                page_num += 1
                season_json = self._download_json(
                    self._API_EPISODES_URL.format(season_id, next_url),
                    video_id=season_id,
                    headers={'Referer': 'https://mxplayer.in'},
                    note='Downloading JSON metadata page %d' % page_num)
                for episode in season_json.get('items') or []:
                    video_url = episode['webUrl']
                    yield self.url_result(
                        'https://mxplayer.in%s' % video_url,
                        ie=MxplayerIE.ie_key(), video_id=video_url.split('-')[-1])
                next_url = season_json.get('next')

    def _real_extract(self, url):
        display_id, show_id = self._match_valid_url(url).groups()
        return self.playlist_result(
            self._entries(show_id), playlist_id=show_id,
            playlist_title=display_id.replace('-', ' ').title())
