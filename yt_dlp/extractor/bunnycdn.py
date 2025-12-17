import json

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    extract_attributes,
    int_or_none,
    parse_qs,
    smuggle_url,
    unsmuggle_url,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import find_element, traverse_obj


class BunnyCdnIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:iframe|player)\.mediadelivery\.net|video\.bunnycdn\.com)/(?:embed|play)/(?P<library_id>\d+)/(?P<id>[\da-f-]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+src=[\'"](?P<url>{_VALID_URL}[^\'"]*)[\'"]']
    _TESTS = [{
        'url': 'https://iframe.mediadelivery.net/embed/113933/e73edec1-e381-4c8b-ae73-717a140e0924',
        'info_dict': {
            'id': 'e73edec1-e381-4c8b-ae73-717a140e0924',
            'ext': 'mp4',
            'title': 'mistress morgana (3).mp4',
            'description': '',
            'timestamp': 1693251673,
            'thumbnail': r're:^https?://.*\.b-cdn\.net/e73edec1-e381-4c8b-ae73-717a140e0924/thumbnail\.jpg',
            'duration': 7.0,
            'upload_date': '20230828',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://iframe.mediadelivery.net/play/136145/32e34c4b-0d72-437c-9abb-05e67657da34',
        'info_dict': {
            'id': '32e34c4b-0d72-437c-9abb-05e67657da34',
            'ext': 'mp4',
            'timestamp': 1691145748,
            'thumbnail': r're:^https?://.*\.b-cdn\.net/32e34c4b-0d72-437c-9abb-05e67657da34/thumbnail_9172dc16\.jpg',
            'duration': 106.0,
            'description': 'md5:11452bcb31f379ee3eaf1234d3264e44',
            'upload_date': '20230804',
            'title': 'Sanela ist Teil der #arbeitsmarktkraft',
        },
        'params': {'skip_download': True},
    }, {
        # Stream requires activation and pings
        'url': 'https://iframe.mediadelivery.net/embed/200867/2e8545ec-509d-4571-b855-4cf0235ccd75',
        'info_dict': {
            'id': '2e8545ec-509d-4571-b855-4cf0235ccd75',
            'ext': 'mp4',
            'timestamp': 1708497752,
            'title': 'netflix part 1',
            'duration': 3959.0,
            'description': '',
            'upload_date': '20240221',
            'thumbnail': r're:^https?://.*\.b-cdn\.net/2e8545ec-509d-4571-b855-4cf0235ccd75/thumbnail\.jpg',
        },
        'params': {'skip_download': True},
    }, {
        # Requires any Referer
        'url': 'https://iframe.mediadelivery.net/embed/289162/6372f5a3-68df-4ef7-a115-e1110186c477',
        'info_dict': {
            'id': '6372f5a3-68df-4ef7-a115-e1110186c477',
            'ext': 'mp4',
            'title': '12-Creating Small Asset Blockouts -Timelapse.mp4',
            'description': '',
            'duration': 263.0,
            'timestamp': 1724485440,
            'upload_date': '20240824',
            'thumbnail': r're:^https?://.*\.b-cdn\.net/6372f5a3-68df-4ef7-a115-e1110186c477/thumbnail\.jpg',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://player.mediadelivery.net/embed/519128/875880a9-bcc2-4038-9e05-e5024bba9b70',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # Stream requires Referer
        'url': 'https://conword.io/',
        'info_dict': {
            'id': '3a5d863e-9cd6-447e-b6ef-e289af50b349',
            'ext': 'mp4',
            'title': 'Conword bei der Stadt Köln und Stadt Dortmund',
            'description': '',
            'upload_date': '20231031',
            'duration': 31.0,
            'thumbnail': 'https://video.watchuh.com/3a5d863e-9cd6-447e-b6ef-e289af50b349/thumbnail.jpg',
            'timestamp': 1698783879,
        },
        'params': {'skip_download': True},
    }, {
        # URL requires token and expires
        'url': 'https://www.stockphotos.com/video/moscow-subway-the-train-is-arriving-at-the-park-kultury-station-10017830',
        'info_dict': {
            'id': '0b02fa20-4e8c-4140-8f87-f64d820a3386',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.b-cdn\.net/0b02fa20-4e8c-4140-8f87-f64d820a3386/thumbnail\.jpg',
            'title': 'Moscow subway. The train is arriving at the Park Kultury station.',
            'upload_date': '20240531',
            'duration': 18.0,
            'timestamp': 1717152269,
            'description': '',
        },
        'params': {'skip_download': True},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            yield smuggle_url(embed_url, {'Referer': url})

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        video_id, library_id = self._match_valid_url(url).group('id', 'library_id')
        webpage = self._download_webpage(
            f'https://iframe.mediadelivery.net/embed/{library_id}/{video_id}', video_id,
            headers={'Referer': smuggled_data.get('Referer') or 'https://iframe.mediadelivery.net/'},
            query=traverse_obj(parse_qs(url), {'token': 'token', 'expires': 'expires'}))

        if html_title := self._html_extract_title(webpage, default=None) == '403':
            raise ExtractorError(
                'This video is inaccessible. Setting a Referer header '
                'might be required to access the video', expected=True)
        elif html_title == '404':
            raise ExtractorError('This video does not exist', expected=True)

        headers = {'Referer': url}

        info = traverse_obj(self._parse_html5_media_entries(url, webpage, video_id, _headers=headers), 0) or {}
        formats = info.get('formats') or []
        subtitles = info.get('subtitles') or {}

        original_url = self._search_regex(
            r'(?:var|const|let)\s+originalUrl\s*=\s*["\']([^"\']+)["\']', webpage, 'original url', default=None)
        if url_or_none(original_url):
            urlh = self._request_webpage(
                HEADRequest(original_url), video_id=video_id, note='Checking original',
                headers=headers, fatal=False, expected_status=(403, 404))
            if urlh and urlh.status == 200:
                formats.append({
                    'url': original_url,
                    'format_id': 'source',
                    'quality': 1,
                    'http_headers': headers,
                    'ext': urlhandle_detect_ext(urlh, default='mp4'),
                    'filesize': int_or_none(urlh.get_header('Content-Length')),
                })

        # MediaCage Streams require activation and pings
        src_url = self._search_regex(
            r'\.setAttribute\([\'"]src[\'"],\s*[\'"]([^\'"]+)[\'"]\)', webpage, 'src url', default=None)
        activation_url = self._search_regex(
            r'loadUrl\([\'"]([^\'"]+/activate)[\'"]', webpage, 'activation url', default=None)
        ping_url = self._search_regex(
            r'loadUrl\([\'"]([^\'"]+/ping)[\'"]', webpage, 'ping url', default=None)
        secret = traverse_obj(parse_qs(src_url), ('secret', 0))
        context_id = traverse_obj(parse_qs(src_url), ('contextId', 0))
        ping_data = {}
        if src_url and activation_url and ping_url and secret and context_id:
            self._download_webpage(
                activation_url, video_id, headers=headers, note='Downloading activation data')

            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                src_url, video_id, 'mp4', headers=headers, m3u8_id='hls', fatal=False)
            for fmt in fmts:
                fmt.update({
                    'protocol': 'bunnycdn',
                    'http_headers': headers,
                })
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

            ping_data = {
                '_bunnycdn_ping_data': {
                    'url': ping_url,
                    'headers': headers,
                    'secret': secret,
                    'context_id': context_id,
                },
            }

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(webpage, ({find_element(id='main-video', html=True)}, {extract_attributes}, {
                'title': ('data-plyr-config', {json.loads}, 'title', {str}),
                'thumbnail': ('data-poster', {url_or_none}),
            })),
            **ping_data,
            **self._search_json_ld(webpage, video_id, fatal=False),
        }
