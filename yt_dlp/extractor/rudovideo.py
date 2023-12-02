from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj, js_to_json, update_url_query


class RudoVideoLiveIE(InfoExtractor):
    _VALID_URL = r'https?://rudo\.video/(?P<type>live|vod|podcast)/(?P<id>[^/?]+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=[\'"](?P<url>(?:https?:)//rudo\.video/(?:live|vod|podcast)/[^\'"]+)']
    _TESTS = [{
        'url': 'https://rudo.video/podcast/cz2wrUy8l0o',
        'md5': '28ed82b477708dc5e12e072da2449221',
        'info_dict': {
            'id': 'cz2wrUy8l0o',
            'title': 'Diego Cabot',
            'ext': 'mp4',
            'thumbnail': r're:^(?:https?:)?//.*\.(png|jpg)$',
        },
    }, {
        'url': 'https://rudo.video/podcast/bQkt07',
        'md5': '36b22a9863de0f47f00fc7532a32a898',
        'info_dict': {
            'id': 'bQkt07',
            'title': 'Tubular Bells',
            'ext': 'mp4',
            'thumbnail': r're:^(?:https?:)?//.*\.(png|jpg)$',
        },
    }, {
        'url': 'https://rudo.video/vod/bN5AaJ',
        'md5': '01324a329227e2591530ecb4f555c881',
        'info_dict': {
            'id': 'bN5AaJ',
            'title': 'Ucrania 19.03',
            'creator': 'La Tercera',
            'ext': 'mp4',
            'thumbnail': r're:^(?:https?:)?//.*\.(png|jpg)$',
        },
    }, {
        'url': 'https://rudo.video/live/bbtv',
        'info_dict': {
            'id': 'bbtv',
            'ext': 'mp4',
            'creator': 'BioBioTV',
            'live_status': 'is_live',
            'title': r're:^LIVE BBTV\s\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}$',
            'thumbnail': r're:^(?:https?:)?//.*\.(png|jpg)$',
        },
    }, {
        'url': 'https://rudo.video/live/c13',
        'info_dict': {
            'id': 'c13',
            'title': 'CANAL13',
            'ext': 'mp4',
        },
        'skip': 'Geo-restricted to Chile',
    }, {
        'url': 'https://rudo.video/live/t13-13cl',
        'info_dict': {
            'id': 't13-13cl',
            'title': 'T13',
            'ext': 'mp4',
        },
        'skip': 'Geo-restricted to Chile',
    }]

    def get_title(self, webpage):
        title = self._search_regex(r'var\s+titleVideo\s*=\s*[\'"]([^\'"]+)', webpage, 'title', default=None)
        if title is None:
            title = self._search_regex(r'<meta[^>]+property=[\'"]og:title[\'"]\s+content=[\'"]([^\'"]+)', webpage, 'title', fatal=False)
        return title

    def get_thumbnail(self, webpage):
        thumbnail = self._search_regex(r'var\s+posterIMG\s*=\s*[\'"]([^?\'"]+)', webpage, 'thumbnail', default=None)
        if thumbnail is None:
            thumbnail = self._search_regex(r'<meta[^>]+property=[\'"]og:image[\'"]\s+content=[\'"]([^\'"]+)', webpage, 'thumbnail', default=None)
        return thumbnail

    def _real_extract(self, url):
        video_id = self._match_id(url)
        type = self._match_valid_url(url).group('type')
        webpage = self._download_webpage(url, video_id)

        if 'Streaming is not available in your area.' in webpage:
            self.raise_geo_restricted()

        stream_url = self._search_regex(r'var\s+streamURL\s*=\s*[\'"]([^?\'"]+)', webpage, 'streamUrl', default=None)
        source_url = self._search_regex(r'<source[^>]+src=[\'"]([^\'"]+)', webpage, 'sourceUrl', default=None)
        youtube_url = self._search_regex(r'file:\s*[\'"]((?:https?:)//(?:www\.)?youtube.com[^\'"]+)', webpage, 'youtubeUrl', default=None)
        if stream_url is None:
            if source_url is not None:
                stream_url = source_url
            elif youtube_url is not None:
                return self.url_result(youtube_url, display_id=video_id)
            else:
                raise ExtractorError('Unable to extract stream url')

        title = self.get_title(webpage)
        thumbnail = self.get_thumbnail(webpage)
        is_live = None
        if type == 'live':
            is_live = True

        token_array = self._search_json(r'<script>var\s+_\$_[a-zA-Z0-9]+\s*=', webpage, 'access token array', video_id,
                                        contains_pattern=r'\[(?s:.+)\]', default=None, transform_source=js_to_json)
        if token_array:
            if len(token_array) != 9:
                raise ExtractorError('Couldnt get access token array', video_id=video_id)
            access_token = self._download_json(token_array[0], video_id, note='Downloading access token')
            stream_url = update_url_query(stream_url, {'auth-token': traverse_obj(access_token, ('data', 'authToken'))})

        return {
            'id': video_id,
            'title': title,
            'formats': self._extract_m3u8_formats(stream_url, video_id, live=True),
            'is_live': is_live,
            'creator': self._search_regex(r'var\s+videoAuthor\s*=\s*[\'"]([^?\'"]+)', webpage, "videoAuthor", default=None),
            'thumbnail': thumbnail,
        }
