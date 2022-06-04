import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    urlencode_postdata,
    compat_str,
    ExtractorError,
)


class CuriosityStreamBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'curiositystream'
    _auth_token = None

    def _handle_errors(self, result):
        error = result.get('error', {}).get('message')
        if error:
            if isinstance(error, dict):
                error = ', '.join(error.values())
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, error), expected=True)

    def _call_api(self, path, video_id, query=None):
        headers = {}
        if not self._auth_token:
            auth_cookie = self._get_cookies('https://curiositystream.com').get('auth_token')
            if auth_cookie:
                self.write_debug('Obtained auth_token cookie')
                self._auth_token = auth_cookie.value
        if self._auth_token:
            headers['X-Auth-Token'] = self._auth_token
        result = self._download_json(
            self._API_BASE_URL + path, video_id, headers=headers, query=query)
        self._handle_errors(result)
        return result['data']

    def _perform_login(self, username, password):
        result = self._download_json(
            'https://api.curiositystream.com/v1/login', None,
            note='Logging in', data=urlencode_postdata({
                'email': username,
                'password': password,
            }))
        self._handle_errors(result)
        CuriosityStreamBaseIE._auth_token = result['message']['auth_token']


class CuriosityStreamIE(CuriosityStreamBaseIE):
    IE_NAME = 'curiositystream'
    _VALID_URL = r'https?://(?:app\.)?curiositystream\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://app.curiositystream.com/video/2',
        'info_dict': {
            'id': '2',
            'ext': 'mp4',
            'title': 'How Did You Develop The Internet?',
            'description': 'Vint Cerf, Google\'s Chief Internet Evangelist, describes how he and Bob Kahn created the internet.',
            'channel': 'Curiosity Stream',
            'categories': ['Technology', 'Interview'],
            'average_rating': 96.79,
            'series_id': '2',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _API_BASE_URL = 'https://api.curiositystream.com/v1/media/'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats = []
        for encoding_format in ('m3u8', 'mpd'):
            media = self._call_api(video_id, video_id, query={
                'encodingsNew': 'true',
                'encodingsFormat': encoding_format,
            })
            for encoding in media.get('encodings', []):
                playlist_url = encoding.get('master_playlist_url')
                if encoding_format == 'm3u8':
                    # use `m3u8` entry_protocol until EXT-X-MAP is properly supported by `m3u8_native` entry_protocol
                    formats.extend(self._extract_m3u8_formats(
                        playlist_url, video_id, 'mp4',
                        m3u8_id='hls', fatal=False))
                elif encoding_format == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        playlist_url, video_id, mpd_id='dash', fatal=False))
                encoding_url = encoding.get('url')
                file_url = encoding.get('file_url')
                if not encoding_url and not file_url:
                    continue
                f = {
                    'width': int_or_none(encoding.get('width')),
                    'height': int_or_none(encoding.get('height')),
                    'vbr': int_or_none(encoding.get('video_bitrate')),
                    'abr': int_or_none(encoding.get('audio_bitrate')),
                    'filesize': int_or_none(encoding.get('size_in_bytes')),
                    'vcodec': encoding.get('video_codec'),
                    'acodec': encoding.get('audio_codec'),
                    'container': encoding.get('container_type'),
                }
                for f_url in (encoding_url, file_url):
                    if not f_url:
                        continue
                    fmt = f.copy()
                    rtmp = re.search(r'^(?P<url>rtmpe?://(?P<host>[^/]+)/(?P<app>.+))/(?P<playpath>mp[34]:.+)$', f_url)
                    if rtmp:
                        fmt.update({
                            'url': rtmp.group('url'),
                            'play_path': rtmp.group('playpath'),
                            'app': rtmp.group('app'),
                            'ext': 'flv',
                            'format_id': 'rtmp',
                        })
                    else:
                        fmt.update({
                            'url': f_url,
                            'format_id': 'http',
                        })
                    formats.append(fmt)
        self._sort_formats(formats)

        title = media['title']

        subtitles = {}
        for closed_caption in media.get('closed_captions', []):
            sub_url = closed_caption.get('file')
            if not sub_url:
                continue
            lang = closed_caption.get('code') or closed_caption.get('language') or 'en'
            subtitles.setdefault(lang, []).append({
                'url': sub_url,
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': media.get('description'),
            'thumbnail': media.get('image_large') or media.get('image_medium') or media.get('image_small'),
            'duration': int_or_none(media.get('duration')),
            'tags': media.get('tags'),
            'subtitles': subtitles,
            'channel': media.get('producer'),
            'categories': [media.get('primary_category'), media.get('type')],
            'average_rating': media.get('rating_percentage'),
            'series_id': str(media.get('collection_id') or '') or None,
        }


class CuriosityStreamCollectionBaseIE(CuriosityStreamBaseIE):

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        collection = self._call_api(collection_id, collection_id)
        entries = []
        for media in collection.get('media', []):
            media_id = compat_str(media.get('id'))
            media_type, ie = ('series', CuriosityStreamSeriesIE) if media.get('is_collection') else ('video', CuriosityStreamIE)
            entries.append(self.url_result(
                'https://curiositystream.com/%s/%s' % (media_type, media_id),
                ie=ie.ie_key(), video_id=media_id))
        return self.playlist_result(
            entries, collection_id,
            collection.get('title'), collection.get('description'))


class CuriosityStreamCollectionsIE(CuriosityStreamCollectionBaseIE):
    IE_NAME = 'curiositystream:collections'
    _VALID_URL = r'https?://(?:app\.)?curiositystream\.com/collections/(?P<id>\d+)'
    _API_BASE_URL = 'https://api.curiositystream.com/v2/collections/'
    _TESTS = [{
        'url': 'https://curiositystream.com/collections/86',
        'info_dict': {
            'id': '86',
            'title': 'Staff Picks',
            'description': 'Wondering where to start? Here are a few of our favorite series and films... from our couch to yours.',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://curiositystream.com/collections/36',
        'only_matching': True,
    }]


class CuriosityStreamSeriesIE(CuriosityStreamCollectionBaseIE):
    IE_NAME = 'curiositystream:series'
    _VALID_URL = r'https?://(?:app\.)?curiositystream\.com/(?:series|collection)/(?P<id>\d+)'
    _API_BASE_URL = 'https://api.curiositystream.com/v2/series/'
    _TESTS = [{
        'url': 'https://curiositystream.com/series/2',
        'info_dict': {
            'id': '2',
            'title': 'Curious Minds: The Internet',
            'description': 'How is the internet shaping our lives in the 21st Century?',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://curiositystream.com/collection/2',
        'only_matching': True,
    }]
