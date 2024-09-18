from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    parse_codecs,
    try_get,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class DigitalConcertHallIE(InfoExtractor):
    IE_DESC = 'DigitalConcertHall extractor'
    _VALID_URL = r'https?://(?:www\.)?digitalconcerthall\.com/(?P<language>[a-z]+)/(?P<type>film|concert|work)/(?P<id>[0-9]+)-?(?P<part>[0-9]+)?'
    _OAUTH_URL = 'https://api.digitalconcerthall.com/v2/oauth2/token'
    _USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15'
    _ACCESS_TOKEN = None
    _NETRC_MACHINE = 'digitalconcerthall'
    _TESTS = [{
        'note': 'Playlist with only one video',
        'url': 'https://www.digitalconcerthall.com/en/concert/53201',
        'info_dict': {
            'id': '53201-1',
            'ext': 'mp4',
            'composer': 'Kurt Weill',
            'title': '[Magic Night]',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
            'upload_date': '20210624',
            'timestamp': 1624548600,
            'duration': 2798,
            'album_artists': ['Members of the Berliner Philharmoniker', 'Simon Rössler'],
            'composers': ['Kurt Weill'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Concert with several works and an interview',
        'url': 'https://www.digitalconcerthall.com/en/concert/53785',
        'info_dict': {
            'id': '53785',
            'album_artists': ['Berliner Philharmoniker', 'Kirill Petrenko'],
            'title': 'Kirill Petrenko conducts Mendelssohn and Shostakovich',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
        'playlist_count': 3,
    }, {
        'url': 'https://www.digitalconcerthall.com/en/film/388',
        'info_dict': {
            'id': '388',
            'ext': 'mp4',
            'title': 'The Berliner Philharmoniker and Frank Peter Zimmermann',
            'description': 'md5:cfe25a7044fa4be13743e5089b5b5eb2',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
            'upload_date': '20220714',
            'timestamp': 1657785600,
            'album_artists': ['Frank Peter Zimmermann', 'Benedikt von Bernstorff', 'Jakob von Bernstorff'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Concert with several works and an interview',
        'url': 'https://www.digitalconcerthall.com/en/work/53785-1',
        'info_dict': {
            'id': '53785',
            'album_artists': ['Berliner Philharmoniker', 'Kirill Petrenko'],
            'title': 'Kirill Petrenko conducts Mendelssohn and Shostakovich',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
        'playlist_count': 1,
    }]

    def _perform_login(self, username, password):
        login_token = self._download_json(
            self._OAUTH_URL,
            None, 'Obtaining token', errnote='Unable to obtain token', data=urlencode_postdata({
                'affiliate': 'none',
                'grant_type': 'device',
                'device_vendor': 'unknown',
                # device_model 'Safari' gets split streams of 4K/HEVC video and lossless/FLAC audio
                'device_model': 'unknown' if self._configuration_arg('prefer_combined_hls') else 'Safari',
                'app_id': 'dch.webapp',
                'app_distributor': 'berlinphil',
                'app_version': '1.84.0',
                'client_secret': '2ySLN+2Fwb',
            }), headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'User-Agent': self._USER_AGENT,
            })['access_token']
        try:
            login_response = self._download_json(
                self._OAUTH_URL,
                None, note='Logging in', errnote='Unable to login', data=urlencode_postdata({
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                }), headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    'Referer': 'https://www.digitalconcerthall.com',
                    'Authorization': f'Bearer {login_token}',
                    'User-Agent': self._USER_AGENT,
                })
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 401:
                raise ExtractorError('Invalid username or password', expected=True)
            raise
        self._ACCESS_TOKEN = login_response['access_token']

    def _real_initialize(self):
        if not self._ACCESS_TOKEN:
            self.raise_login_required(method='password')

    def _entries(self, items, language, type_, **kwargs):
        for item in items:
            video_id = item['id']
            stream_info = self._download_json(
                self._proto_relative_url(item['_links']['streams']['href']), video_id, headers={
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self._ACCESS_TOKEN}',
                    'Accept-Language': language,
                    'User-Agent': self._USER_AGENT,
                })

            formats = []
            for m3u8_url in traverse_obj(stream_info, ('channel', ..., 'stream', ..., 'url', {url_or_none})):
                formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
            for fmt in formats:
                if fmt.get('format_note') and fmt.get('vcodec') == 'none':
                    fmt.update(parse_codecs(fmt['format_note']))

            yield {
                'id': video_id,
                'title': item.get('title'),
                'composer': item.get('name_composer'),
                'formats': formats,
                'duration': item.get('duration_total'),
                'timestamp': traverse_obj(item, ('date', 'published')),
                'description': item.get('short_description') or stream_info.get('short_description'),
                **kwargs,
                'chapters': [{
                    'start_time': chapter.get('time'),
                    'end_time': try_get(chapter, lambda x: x['time'] + x['duration']),
                    'title': chapter.get('text'),
                } for chapter in item['cuepoints']] if item.get('cuepoints') and type_ == 'concert' else None,
            }

    def _real_extract(self, url):
        language, type_, video_id, part = self._match_valid_url(url).group('language', 'type', 'id', 'part')
        if not language:
            language = 'en'

        api_type = 'concert' if type_ == 'work' else type_
        vid_info = self._download_json(
            f'https://api.digitalconcerthall.com/v2/{api_type}/{video_id}', video_id, headers={
                'Accept': 'application/json',
                'Accept-Language': language,
                'User-Agent': self._USER_AGENT,
                'Authorization': f'Bearer {self._ACCESS_TOKEN}',
            })
        videos = [vid_info] if type_ == 'film' else traverse_obj(vid_info, ('_embedded', ..., ...))

        if type_ == 'work':
            videos = [videos[int(part) - 1]]

        album_artists = traverse_obj(vid_info, ('_links', 'artist', ..., 'name', {str}))
        thumbnail = traverse_obj(vid_info, (
            'image', ..., {self._proto_relative_url}, {url_or_none},
            {lambda x: x.format(width=0, height=0)}, any))  # NB: 0x0 is the original size

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': vid_info.get('title'),
            'entries': self._entries(
                videos, language, type_, thumbnail=thumbnail, album_artists=album_artists),
            'thumbnail': thumbnail,
            'album_artists': album_artists,
        }
