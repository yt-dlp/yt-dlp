from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    parse_resolution,
    traverse_obj,
    try_get,
    urlencode_postdata,
)


class DigitalConcertHallIE(InfoExtractor):
    IE_DESC = 'DigitalConcertHall extractor'
    _VALID_URL = r'https?://(?:www\.)?digitalconcerthall\.com/(?P<language>[a-z]+)/concert/(?P<id>[0-9]+)'
    _OAUTH_URL = 'https://api.digitalconcerthall.com/v2/oauth2/token'
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
            'album_artist': 'Members of the Berliner Philharmoniker / Simon Rössler',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Concert with several works and an interview',
        'url': 'https://www.digitalconcerthall.com/en/concert/53785',
        'info_dict': {
            'id': '53785',
            'album_artist': 'Berliner Philharmoniker / Kirill Petrenko',
            'title': 'Kirill Petrenko conducts Mendelssohn and Shostakovich',
        },
        'params': {'skip_download': 'm3u8'},
        'playlist_count': 3,
    }]

    def _perform_login(self, username, password):
        token_response = self._download_json(
            self._OAUTH_URL,
            None, 'Obtaining token', errnote='Unable to obtain token', data=urlencode_postdata({
                'affiliate': 'none',
                'grant_type': 'device',
                'device_vendor': 'unknown',
                'app_id': 'dch.webapp',
                'app_version': '1.0.0',
                'client_secret': '2ySLN+2Fwb',
            }), headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        self._ACCESS_TOKEN = token_response['access_token']
        try:
            self._download_json(
                self._OAUTH_URL,
                None, note='Logging in', errnote='Unable to login', data=urlencode_postdata({
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://www.digitalconcerthall.com',
                    'Authorization': f'Bearer {self._ACCESS_TOKEN}'
                })
        except ExtractorError:
            self.raise_login_required(msg='Login info incorrect')

    def _real_initialize(self):
        if not self._ACCESS_TOKEN:
            self.raise_login_required(method='password')

    def _entries(self, items, language, **kwargs):
        for item in items:
            video_id = item['id']
            stream_info = self._download_json(
                self._proto_relative_url(item['_links']['streams']['href']), video_id, headers={
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self._ACCESS_TOKEN}',
                    'Accept-Language': language
                })

            m3u8_url = traverse_obj(
                stream_info, ('channel', lambda k, _: k.startswith('vod_mixed'), 'stream', 0, 'url'), get_all=False)
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', 'm3u8_native', fatal=False)
            self._sort_formats(formats)

            yield {
                'id': video_id,
                'title': item.get('title'),
                'composer': item.get('name_composer'),
                'url': m3u8_url,
                'formats': formats,
                'duration': item.get('duration_total'),
                'timestamp': traverse_obj(item, ('date', 'published')),
                'description': item.get('short_description') or stream_info.get('short_description'),
                **kwargs,
                'chapters': [{
                    'start_time': chapter.get('time'),
                    'end_time': try_get(chapter, lambda x: x['time'] + x['duration']),
                    'title': chapter.get('text'),
                } for chapter in item['cuepoints']] if item.get('cuepoints') else None,
            }

    def _real_extract(self, url):
        language, video_id = self._match_valid_url(url).group('language', 'id')
        if not language:
            language = 'en'

        thumbnail_url = self._html_search_regex(
            r'(https?://images\.digitalconcerthall\.com/cms/thumbnails/.*\.jpg)',
            self._download_webpage(url, video_id), 'thumbnail')
        thumbnails = [{
            'url': thumbnail_url,
            **parse_resolution(thumbnail_url)
        }]

        vid_info = self._download_json(
            f'https://api.digitalconcerthall.com/v2/concert/{video_id}', video_id, headers={
                'Accept': 'application/json',
                'Accept-Language': language
            })
        album_artist = ' / '.join(traverse_obj(vid_info, ('_links', 'artist', ..., 'name')) or '')

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': vid_info.get('title'),
            'entries': self._entries(traverse_obj(vid_info, ('_embedded', ..., ...)), language,
                                     thumbnails=thumbnails, album_artist=album_artist),
            'thumbnails': thumbnails,
            'album_artist': album_artist,
        }
