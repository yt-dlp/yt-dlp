import functools
import json
import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    format_field,
    get_element_by_class,
    get_elements_html_by_class,
    int_or_none,
    orderedSet,
    parse_count,
    parse_duration,
    parse_iso8601,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class BitChuteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|old)\.)?bitchute\.com/(?:video|embed|torrent/[^/?#]+)/(?P<id>[^/?#&]+)'
    _EMBED_REGEX = [rf'<(?:script|iframe)[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://www.bitchute.com/video/UGlrF9o9b-Q/',
        'md5': '7e427d7ed7af5a75b5855705ec750e2b',
        'info_dict': {
            'id': 'UGlrF9o9b-Q',
            'ext': 'mp4',
            'title': 'This is the first video on #BitChute !',
            'description': 'md5:a0337e7b1fe39e32336974af8173a034',
            'thumbnail': r're:https?://.+/.+\.jpg$',
            'uploader': 'BitChute',
            'upload_date': '20170103',
            'uploader_url': 'https://www.bitchute.com/profile/I5NgtHZn9vPj/',
            'channel': 'BitChute',
            'channel_url': 'https://www.bitchute.com/channel/bitchute/',
            'uploader_id': 'I5NgtHZn9vPj',
            'channel_id': '1VBwRfyNcKdX',
            'view_count': int,
            'duration': 16.0,
            'timestamp': 1483425443,
        },
    }, {
        # test case: video with different channel and uploader
        'url': 'https://www.bitchute.com/video/Yti_j9A-UZ4/',
        'md5': 'f10e6a8e787766235946d0868703f1d0',
        'info_dict': {
            'id': 'Yti_j9A-UZ4',
            'ext': 'mp4',
            'title': 'Israel at War | Full Measure',
            'description': 'md5:e60198b89971966d6030d22b3268f08f',
            'thumbnail': r're:https?://.+/.+\.jpg$',
            'uploader': 'sharylattkisson',
            'upload_date': '20231106',
            'uploader_url': 'https://www.bitchute.com/profile/9K0kUWA9zmd9/',
            'channel': 'Full Measure with Sharyl Attkisson',
            'channel_url': 'https://www.bitchute.com/channel/sharylattkisson/',
            'uploader_id': '9K0kUWA9zmd9',
            'channel_id': 'NpdxoCRv3ZLb',
            'view_count': int,
            'duration': 554.0,
            'timestamp': 1699296106,
        },
    }, {
        # video not downloadable in browser, but we can recover it
        'url': 'https://www.bitchute.com/video/2s6B3nZjAk7R/',
        'md5': '05c12397d5354bf24494885b08d24ed1',
        'info_dict': {
            'id': '2s6B3nZjAk7R',
            'ext': 'mp4',
            'filesize': 71537926,
            'title': 'STYXHEXENHAMMER666 - Election Fraud, Clinton 2020, EU Armies, and Gun Control',
            'description': 'md5:2029c7c212ccd4b040f52bb2d036ef4e',
            'thumbnail': r're:https?://.+/.+\.jpg$',
            'uploader': 'BitChute',
            'upload_date': '20181113',
            'uploader_url': 'https://www.bitchute.com/profile/I5NgtHZn9vPj/',
            'channel': 'BitChute',
            'channel_url': 'https://www.bitchute.com/channel/bitchute/',
            'uploader_id': 'I5NgtHZn9vPj',
            'channel_id': '1VBwRfyNcKdX',
            'view_count': int,
            'duration': 1701.0,
            'tags': ['bitchute'],
            'timestamp': 1542130287,
        },
        'params': {'check_formats': None},
    }, {
        'url': 'https://www.bitchute.com/embed/lbb5G1hjPhw/',
        'only_matching': True,
    }, {
        'url': 'https://www.bitchute.com/torrent/Zee5BE49045h/szoMrox2JEI.webtorrent',
        'only_matching': True,
    }, {
        'url': 'https://old.bitchute.com/video/UGlrF9o9b-Q/',
        'only_matching': True,
    }]
    _GEO_BYPASS = False
    _UPLOADER_URL_TMPL = 'https://www.bitchute.com/profile/%s/'
    _CHANNEL_URL_TMPL = 'https://www.bitchute.com/channel/%s/'

    def _check_format(self, video_url, video_id):
        urls = orderedSet(
            re.sub(r'(^https?://)(seed\d+)(?=\.bitchute\.com)', fr'\g<1>{host}', video_url)
            for host in (r'\g<2>', 'seed122', 'seed125', 'seed126', 'seed128',
                         'seed132', 'seed150', 'seed151', 'seed152', 'seed153',
                         'seed167', 'seed171', 'seed177', 'seed305', 'seed307',
                         'seedp29xb', 'zb10-7gsop1v78'))
        for url in urls:
            try:
                response = self._request_webpage(
                    HEADRequest(url), video_id=video_id, note=f'Checking {url}')
            except ExtractorError as e:
                self.to_screen(f'{video_id}: URL is invalid, skipping: {e.cause}')
                continue
            return {
                'url': url,
                'filesize': int_or_none(response.headers.get('Content-Length')),
            }

    def _call_api(self, endpoint, data, display_id, fatal=True):
        note = endpoint.rpartition('/')[2]
        try:
            return self._download_json(
                f'https://api.bitchute.com/api/beta/{endpoint}', display_id,
                f'Downloading {note} API JSON', f'Unable to download {note} API JSON',
                data=json.dumps(data).encode(),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                errors = '. '.join(traverse_obj(e.cause.response.read().decode(), (
                    {json.loads}, 'errors', lambda _, v: v['context'] == 'reason', 'message', {str})))
                if errors and 'location' in errors:
                    # Can always be fatal since the video/media call will reach this code first
                    self.raise_geo_restricted(errors)
            if fatal:
                raise
            self.report_warning(e.msg)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = {'video_id': video_id}
        media_url = self._call_api('video/media', data, video_id)['media_url']

        formats = []
        if determine_ext(media_url) == 'm3u8':
            formats.extend(
                self._extract_m3u8_formats(media_url, video_id, 'mp4', m3u8_id='hls', live=True))
        else:
            if self.get_param('check_formats') is not False:
                if fmt := self._check_format(media_url, video_id):
                    formats.append(fmt)
            else:
                formats.append({'url': media_url})

        if not formats:
            self.raise_no_formats(
                'Video is unavailable. Please make sure this video is playable in the browser '
                'before reporting this issue.', expected=True, video_id=video_id)

        video = self._call_api('video', data, video_id, fatal=False)
        channel = None
        if channel_id := traverse_obj(video, ('channel', 'channel_id', {str})):
            channel = self._call_api('channel', {'channel_id': channel_id}, video_id, fatal=False)

        return {
            **traverse_obj(video, {
                'title': ('video_name', {str}),
                'description': ('description', {str}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'channel': ('channel', 'channel_name', {str}),
                'channel_id': ('channel', 'channel_id', {str}),
                'channel_url': ('channel', 'channel_url', {urljoin('https://www.bitchute.com/')}),
                'uploader_id': ('profile_id', {str}),
                'uploader_url': ('profile_id', {format_field(template=self._UPLOADER_URL_TMPL)}, filter),
                'timestamp': ('date_published', {parse_iso8601}),
                'duration': ('duration', {parse_duration}),
                'tags': ('hashtags', ..., {str}, filter, all, filter),
                'view_count': ('view_count', {int_or_none}),
                'is_live': ('state_id', {lambda x: x == 'live'}),
            }),
            **traverse_obj(channel, {
                'channel': ('channel_name', {str}),
                'channel_id': ('channel_id', {str}),
                'channel_url': ('url_slug', {format_field(template=self._CHANNEL_URL_TMPL)}, filter),
                'uploader': ('profile_name', {str}),
                'uploader_id': ('profile_id', {str}),
                'uploader_url': ('profile_id', {format_field(template=self._UPLOADER_URL_TMPL)}, filter),
            }),
            'id': video_id,
            'formats': formats,
        }


class BitChuteChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|old)\.)?bitchute\.com/(?P<type>channel|playlist)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.bitchute.com/channel/bitchute/',
        'info_dict': {
            'id': 'bitchute',
            'title': 'BitChute',
            'description': 'md5:2134c37d64fc3a4846787c402956adac',
        },
        'playlist': [
            {
                'md5': '7e427d7ed7af5a75b5855705ec750e2b',
                'info_dict': {
                    'id': 'UGlrF9o9b-Q',
                    'ext': 'mp4',
                    'title': 'This is the first video on #BitChute !',
                    'description': 'md5:a0337e7b1fe39e32336974af8173a034',
                    'thumbnail': r're:https?://.+/.+\.jpg$',
                    'uploader': 'BitChute',
                    'upload_date': '20170103',
                    'uploader_url': 'https://www.bitchute.com/profile/I5NgtHZn9vPj/',
                    'channel': 'BitChute',
                    'channel_url': 'https://www.bitchute.com/channel/bitchute/',
                    'duration': 16,
                    'view_count': int,
                    'uploader_id': 'I5NgtHZn9vPj',
                    'channel_id': '1VBwRfyNcKdX',
                    'timestamp': 1483425443,
                },
            },
        ],
        'params': {
            'skip_download': True,
            'playlist_items': '-1',
        },
    }, {
        'url': 'https://www.bitchute.com/playlist/wV9Imujxasw9/',
        'playlist_mincount': 20,
        'info_dict': {
            'id': 'wV9Imujxasw9',
            'title': 'Bruce MacDonald and "The Light of Darkness"',
            'description': 'md5:747724ef404eebdfc04277714f81863e',
        },
        'skip': '404 Not Found',
    }, {
        'url': 'https://old.bitchute.com/playlist/wV9Imujxasw9/',
        'only_matching': True,
    }]

    _TOKEN = 'zyG6tQcGPE5swyAEFLqKUwMuMMuF6IO2DZ6ZDQjGfsL0e4dcTLwqkTTul05Jdve7'
    PAGE_SIZE = 25
    HTML_CLASS_NAMES = {
        'channel': {
            'container': 'channel-videos-container',
            'title': 'channel-videos-title',
            'description': 'channel-videos-text',
        },
        'playlist': {
            'container': 'playlist-video',
            'title': 'title',
            'description': 'description',
        },

    }

    @staticmethod
    def _make_url(playlist_id, playlist_type):
        return f'https://old.bitchute.com/{playlist_type}/{playlist_id}/'

    def _fetch_page(self, playlist_id, playlist_type, page_num):
        playlist_url = self._make_url(playlist_id, playlist_type)
        data = self._download_json(
            f'{playlist_url}extend/', playlist_id, f'Downloading page {page_num}',
            data=urlencode_postdata({
                'csrfmiddlewaretoken': self._TOKEN,
                'name': '',
                'offset': page_num * self.PAGE_SIZE,
            }), headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': playlist_url,
                'X-Requested-With': 'XMLHttpRequest',
                'Cookie': f'csrftoken={self._TOKEN}',
            })
        if not data.get('success'):
            return
        classes = self.HTML_CLASS_NAMES[playlist_type]
        for video_html in get_elements_html_by_class(classes['container'], data.get('html')):
            video_id = self._search_regex(
                r'<a\s[^>]*\bhref=["\']/video/([^"\'/]+)', video_html, 'video id', default=None)
            if not video_id:
                continue
            yield self.url_result(
                f'https://www.bitchute.com/video/{video_id}', BitChuteIE, video_id, url_transparent=True,
                title=clean_html(get_element_by_class(classes['title'], video_html)),
                description=clean_html(get_element_by_class(classes['description'], video_html)),
                duration=parse_duration(get_element_by_class('video-duration', video_html)),
                view_count=parse_count(clean_html(get_element_by_class('video-views', video_html))))

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).group('type', 'id')
        webpage = self._download_webpage(self._make_url(playlist_id, playlist_type), playlist_id)

        page_func = functools.partial(self._fetch_page, playlist_id, playlist_type)
        return self.playlist_result(
            OnDemandPagedList(page_func, self.PAGE_SIZE), playlist_id,
            title=self._html_extract_title(webpage, default=None),
            description=self._html_search_meta(
                ('description', 'og:description', 'twitter:description'), webpage, default=None),
            playlist_count=int_or_none(self._html_search_regex(
                r'<span>(\d+)\s+videos?</span>', webpage, 'playlist count', default=None)))
