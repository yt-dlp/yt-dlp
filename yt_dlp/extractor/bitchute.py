import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    OnDemandPagedList,
    clean_html,
    get_element_by_class,
    get_elements_html_by_class,
    int_or_none,
    match_filter_func,
    orderedSet,
    parse_count,
    parse_duration,
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
        'url': 'https://www.bitchute.com/embed/lbb5G1hjPhw/',
        'only_matching': True,
    }, {
        'url': 'https://www.bitchute.com/torrent/Zee5BE49045h/szoMrox2JEI.webtorrent',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.bitchute.com/video/%s' % video_id, video_id, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.57 Safari/537.36',
            })

        format_urls = []
        for mobj in re.finditer(
                r'addWebSeed\s*\(\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage):
            format_urls.append(mobj.group('url'))
        format_urls.extend(re.findall(r'as=(https?://[^&"\']+)', webpage))

        formats = [
            {'url': format_url}
            for format_url in orderedSet(format_urls)]

        if not formats:
            entries = self._parse_html5_media_entries(
                url, webpage, video_id)
            if not entries:
                error = self._html_search_regex(r'<h1 class="page-title">([^<]+)</h1>', webpage, 'error', default='Cannot find video')
                if error == 'Video Unavailable':
                    raise GeoRestrictedError(error)
                raise ExtractorError(error, expected=True)
            formats = entries[0]['formats']

        self._check_formats(formats, video_id)
        self._sort_formats(formats)
        publish_date = clean_html(get_element_by_class('video-publish-date', webpage))

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
            'ignore_no_formats_error': True,
            'match_filter': match_filter_func('id=UGlrF9o9b-Q'),
        },
        'expected_warnings': ['No video formats found!', 'Requested format is not available'],
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

    def _entries(self, playlist_type, playlist_id):
        playlist_url = 'https://www.bitchute.com/%s/%s/' % (playlist_type, playlist_id)

        def fetch_entries(page_num):
            data = self._download_json(
                '%sextend/' % playlist_url, playlist_id,
                'Downloading %s page %d' % (playlist_type, page_num),
                data=urlencode_postdata({
                    'csrfmiddlewaretoken': self._TOKEN,
                    'name': '',
                    'offset': page_num * self.PAGE_SIZE,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': playlist_url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cookie': 'csrftoken=%s' % self._TOKEN,
                })
            if data.get('success') is not True:
                return
            class_name = self.HTML_CLASS_NAMES[playlist_type]
            for video_html in get_elements_html_by_class(class_name['container'], data.get('html')):
                match = re.search(r'<a\b[^>]+\bhref=["\']/video/(?P<id>[^"\'/]+)', video_html)
                video_id = match and match.group('id')
                yield self.url_result(
                    'https://www.bitchute.com/video/%s' % video_id,
                    ie=BitChuteIE, video_id=video_id, url_transparent=True,
                    title=clean_html(get_element_by_class(class_name['title'], video_html)),
                    description=clean_html(get_element_by_class(class_name['description'], video_html)),
                    duration=parse_duration(get_element_by_class('video-duration', video_html)),
                    view_count=parse_count(clean_html(get_element_by_class('video-views', video_html))),
                )
        return OnDemandPagedList(fetch_entries, self.PAGE_SIZE)

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).group('type', 'id')

        webpage = self._download_webpage(
            'https://www.bitchute.com/%s/%s/' % (playlist_type, playlist_id), video_id=playlist_id)
        title = self._html_extract_title(webpage, default=None)
        description = self._html_search_meta(
            ('description', 'og:description', 'twitter:description'), webpage, default=None)
        playlist_count = int_or_none(self._html_search_regex(
            r'<span>(\d+) +videos?</span>', webpage, 'playlist count', default=None), default='N/A')

        return self.playlist_result(
            self._entries(playlist_type, playlist_id),
            playlist_id, title, description, playlist_count=playlist_count)
