from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_urllib_parse_unquote_plus,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    js_to_json,
    KNOWN_EXTENSIONS,
    parse_filesize,
    rot47,
    url_or_none,
    urlencode_postdata,
)


class SharedBaseIE(InfoExtractor):
    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, video_id)

        if self._FILE_NOT_FOUND in webpage:
            raise ExtractorError(
                'Video %s does not exist' % video_id, expected=True)

        video_url = self._extract_video_url(webpage, video_id, url)

        title = self._extract_title(webpage)
        filesize = int_or_none(self._extract_filesize(webpage))

        return {
            'id': video_id,
            'url': video_url,
            'ext': 'mp4',
            'filesize': filesize,
            'title': title,
        }

    def _extract_title(self, webpage):
        return compat_b64decode(self._html_search_meta(
            'full:title', webpage, 'title')).decode('utf-8')

    def _extract_filesize(self, webpage):
        return self._html_search_meta(
            'full:size', webpage, 'file size', fatal=False)


class SharedIE(SharedBaseIE):
    IE_DESC = 'shared.sx'
    _VALID_URL = r'https?://shared\.sx/(?P<id>[\da-z]{10})'
    _FILE_NOT_FOUND = '>File does not exist<'

    _TEST = {
        'url': 'http://shared.sx/0060718775',
        'md5': '106fefed92a8a2adb8c98e6a0652f49b',
        'info_dict': {
            'id': '0060718775',
            'ext': 'mp4',
            'title': 'Bmp4',
            'filesize': 1720110,
        },
    }

    def _extract_video_url(self, webpage, video_id, url):
        download_form = self._hidden_inputs(webpage)

        video_page = self._download_webpage(
            url, video_id, 'Downloading video page',
            data=urlencode_postdata(download_form),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': url,
            })

        video_url = self._html_search_regex(
            r'data-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            video_page, 'video URL', group='url')

        return video_url


class VivoIE(SharedBaseIE):
    IE_DESC = 'vivo.sx'
    _VALID_URL = r'https?://vivo\.s[xt]/(?P<id>[\da-z]{10})'
    _FILE_NOT_FOUND = '>The file you have requested does not exists or has been removed'

    _TESTS = [{
        'url': 'http://vivo.sx/d7ddda0e78',
        'md5': '15b3af41be0b4fe01f4df075c2678b2c',
        'info_dict': {
            'id': 'd7ddda0e78',
            'ext': 'mp4',
            'title': 'Chicken',
            'filesize': 515659,
        },
    }, {
        'url': 'http://vivo.st/d7ddda0e78',
        'only_matching': True,
    }]

    def _extract_title(self, webpage):
        title = self._html_search_regex(
            r'data-name\s*=\s*(["\'])(?P<title>(?:(?!\1).)+)\1', webpage,
            'title', default=None, group='title')
        if title:
            ext = determine_ext(title)
            if ext.lower() in KNOWN_EXTENSIONS:
                title = title.rpartition('.' + ext)[0]
            return title
        return self._og_search_title(webpage)

    def _extract_filesize(self, webpage):
        return parse_filesize(self._search_regex(
            r'data-type=["\']video["\'][^>]*>Watch.*?<strong>\s*\((.+?)\)',
            webpage, 'filesize', fatal=False))

    def _extract_video_url(self, webpage, video_id, url):
        def decode_url_old(encoded_url):
            return compat_b64decode(encoded_url).decode('utf-8')

        stream_url = self._search_regex(
            r'data-stream\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'stream url', default=None, group='url')
        if stream_url:
            stream_url = url_or_none(decode_url_old(stream_url))
        if stream_url:
            return stream_url

        def decode_url(encoded_url):
            return rot47(compat_urllib_parse_unquote_plus(encoded_url))

        return decode_url(self._parse_json(
            self._search_regex(
                r'(?s)InitializeStream\s*\(\s*({.+?})\s*\)\s*;', webpage,
                'stream'),
            video_id, transform_source=js_to_json)['source'])
