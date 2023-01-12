import functools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    HEADRequest,
    OnDemandPagedList,
    clean_html,
    get_element_by_class,
    get_element_by_id,
    get_elements_html_by_class,
    int_or_none,
    orderedSet,
    parse_count,
    parse_duration,
    traverse_obj,
    unified_strdate,
    urlencode_postdata,
)


class BitChuteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/(?:video|embed|torrent/[^/]+)/(?P<id>[^/?#&]+)'
    _EMBED_REGEX = [rf'<(?:script|iframe)[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://www.bitchute.com/video/UGlrF9o9b-Q/',
        'md5': '7e427d7ed7af5a75b5855705ec750e2b',
        'info_dict': {
            'id': 'UGlrF9o9b-Q',
            'ext': 'mp4',
            'title': 'This is the first video on #BitChute !',
            'description': 'md5:a0337e7b1fe39e32336974af8173a034',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'BitChute',
            'upload_date': '20170103',
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
            'description': 'md5:228ee93bd840a24938f536aeac9cf749',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'BitChute',
            'upload_date': '20181113',
        },
        'params': {'check_formats': None},
    }, {
        # restricted video
        'url': 'https://www.bitchute.com/video/WEnQU7XGcTdl/',
        'info_dict': {
            'id': 'WEnQU7XGcTdl',
            'ext': 'mp4',
            'title': 'Impartial Truth - Ein Letzter Appell an die Vernunft',
        },
        'params': {'skip_download': True},
        'skip': 'Georestricted in DE',
    }, {
        'url': 'https://www.bitchute.com/embed/lbb5G1hjPhw/',
        'only_matching': True,
    }, {
        'url': 'https://www.bitchute.com/torrent/Zee5BE49045h/szoMrox2JEI.webtorrent',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    _HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.57 Safari/537.36',
        'Referer': 'https://www.bitchute.com/',
    }

    def _check_format(self, video_url, video_id):
        urls = orderedSet(
            re.sub(r'(^https?://)(seed\d+)(?=\.bitchute\.com)', fr'\g<1>{host}', video_url)
            for host in (r'\g<2>', 'seed150', 'seed151', 'seed152', 'seed153'))
        for url in urls:
            try:
                response = self._request_webpage(
                    HEADRequest(url), video_id=video_id, note=f'Checking {url}', headers=self._HEADERS)
            except ExtractorError as e:
                self.to_screen(f'{video_id}: URL is invalid, skipping: {e.cause}')
                continue
            return {
                'url': url,
                'filesize': int_or_none(response.headers.get('Content-Length'))
            }

    def _raise_if_restricted(self, webpage):
        page_title = clean_html(get_element_by_class('page-title', webpage)) or ''
        if re.fullmatch(r'(?:Channel|Video) Restricted', page_title):
            reason = clean_html(get_element_by_id('page-detail', webpage)) or page_title
            self.raise_geo_restricted(reason)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://www.bitchute.com/video/{video_id}', video_id, headers=self._HEADERS)

        self._raise_if_restricted(webpage)
        publish_date = clean_html(get_element_by_class('video-publish-date', webpage))
        entries = self._parse_html5_media_entries(url, webpage, video_id)

        formats = []
        for format_ in traverse_obj(entries, (0, 'formats', ...)):
            if self.get_param('check_formats') is not False:
                format_.update(self._check_format(format_.pop('url'), video_id) or {})
                if 'url' not in format_:
                    continue
            formats.append(format_)

        if not formats:
            self.raise_no_formats(
                'Video is unavailable. Please make sure this video is playable in the browser '
                'before reporting this issue.', expected=True, video_id=video_id)

        return {
            'id': video_id,
            'title': self._html_extract_title(webpage) or self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': clean_html(get_element_by_class('owner', webpage)),
            'upload_date': unified_strdate(self._search_regex(
                r'at \d+:\d+ UTC on (.+?)\.', publish_date, 'upload date', fatal=False)),
            'formats': formats,
        }


class BitChuteChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/(?P<type>channel|playlist)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.bitchute.com/channel/bitchute/',
        'info_dict': {
            'id': 'bitchute',
            'title': 'BitChute',
            'description': 'md5:5329fb3866125afa9446835594a9b138',
        },
        'playlist': [
            {
                'md5': '7e427d7ed7af5a75b5855705ec750e2b',
                'info_dict': {
                    'id': 'UGlrF9o9b-Q',
                    'ext': 'mp4',
                    'filesize': None,
                    'title': 'This is the first video on #BitChute !',
                    'description': 'md5:a0337e7b1fe39e32336974af8173a034',
                    'thumbnail': r're:^https?://.*\.jpg$',
                    'uploader': 'BitChute',
                    'upload_date': '20170103',
                    'duration': 16,
                    'view_count': int,
                },
            }
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
            'description': 'md5:04913227d2714af1d36d804aa2ab6b1e',
        }
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
        }

    }

    @staticmethod
    def _make_url(playlist_id, playlist_type):
        return f'https://www.bitchute.com/{playlist_type}/{playlist_id}/'

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
