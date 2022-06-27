from .common import InfoExtractor
from ..compat import compat_str
from ..utils import try_get


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-my-girlfriend-is-an-alien-hindi-dubbed/season-1/episode-1-online-9d2013d31d5835bb8400e3b3c5e7bb72',
        'info_dict': {
            'id': '9d2013d31d5835bb8400e3b3c5e7bb72',
            'ext': 'mp4',
            'title': 'Episode 1',
            'description': 'md5:62ed43eb9fec5efde5cf3bd1040b7670',
            'season_number': 1,
            'episode_number': 1,
            'duration': 2451,
            'season': 'Season 1',
            'series': 'My Girlfriend Is An Alien (Hindi Dubbed)',
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/9d2013d31d5835bb8400e3b3c5e7bb72/en/16x9/320x180/9562f5f8df42cad09c9a9c4e69eb1567_1920x1080.webp',
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
            'ext': 'mp4',
            'title': 'Knock Knock (Hindi Dubbed)',
            'description': 'md5:b195ba93ff1987309cfa58e2839d2a5b',
            'season_number': 0,
            'episode_number': 0,
            'duration': 5970,
            'season': 'Season 0',
            'series': None,
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/b9fa28df3bfb8758874735bbd7d2655a/en/16x9/320x180/test_pic1588676032011.webp',
            'episode': 'Episode 0'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
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
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/45055d5bcff169ad48f2ad7552a83d6c/en/16x9/320x180/voot_8e7d5f8d8183340869279c732c1e3a43.webp',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-aashram/chapter-1/duh-swapna-online-d445579792b0135598ba1bc9088a84cb',
        'info_dict': {
            'id': 'd445579792b0135598ba1bc9088a84cb',
            'ext': 'mp4',
            'title': 'Duh Swapna',
            'description': 'md5:35ff39c4bdac403c53be1e16a04192d8',
            'season_number': 1,
            'episode_number': 3,
            'duration': 2568,
            'season': 'Chapter 1',
            'series': 'Aashram',
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/d445579792b0135598ba1bc9088a84cb/en/4x3/1600x1200/test_pic1624819307993.webp',
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
            'ext': 'mp4',
            'title': 'Chapter 1',
            'description': 'md5:233886b8598bc91648ac098abe1d288f',
            'season_number': 1,
            'episode_number': 1,
            'duration': 1305,
            'season': 'Season 1',
            'series': 'Dangerous',
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/5a351b4f9fb69436f6bd6ae3a1a75292/en/4x3/1600x1200/test_pic1624706302350.webp',
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
            'season_number': 0,
            'episode_number': 0,
            'duration': 6085,
            'season': 'Season 0',
            'series': None,
            'thumbnail': 'https://qqcdnpictest.mxplay.com/pic/0452f0d80226c398d63ce7e3ea40fa2d/en/16x9/320x180/00c8955dab5e5d340dbde643f9b1f6fd_1920x1080.webp',
            'episode': 'Episode 0'
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        type, display_id, video_id = self._match_valid_url(url).groups()
        type = 'movie_film' if type == 'movie' else 'tvshow_episode'
        API_URL = 'https://androidapi.mxplay.com/v1/detail/'
        headers = {
            'X-Av-Code': '23',
            'X-Country': 'IN',
            'X-Platform': 'android',
            'X-App-Version': '1370001318',
            'X-Resolution': '3840x2160',
        }
        data_json = self._download_json(f'{API_URL}{type}/{video_id}', display_id, headers=headers)['profile']

        season, series = None, None
        for dct in data_json.get('levelInfos', []):
            if dct.get('type') == 'tvshow_season':
                season = dct.get('name')
            elif dct.get('type') == 'tvshow_show':
                series = dct.get('name')
        thumbnails = []
        for thumb in data_json.get('poster', []):
            thumbnails.append({
                'url': thumb.get('url'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
            })

        formats = []
        subtitles = {}
        for dct in data_json.get('playInfo', []):
            if dct.get('extension') == 'mpd':
                frmt, subs = self._extract_mpd_formats_and_subtitles(dct.get('playUrl'), display_id, fatal=False)
                formats.extend(frmt)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif dct.get('extension') == 'm3u8':
                frmt, subs = self._extract_m3u8_formats_and_subtitles(dct.get('playUrl'), display_id, fatal=False)
                formats.extend(frmt)
                subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': data_json.get('name') or display_id,
            'description': data_json.get('description'),
            'season_number': data_json.get('seasonNum'),
            'episode_number': data_json.get('episodeNum'),
            'duration': data_json.get('duration'),
            'season': season,
            'series': series,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
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
