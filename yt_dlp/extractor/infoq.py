from .bokecc import BokeCCBaseIE
from ..compat import (
    compat_b64decode,
    compat_urllib_parse_unquote,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    determine_ext,
    traverse_obj,
    update_url_query,
)


class InfoQIE(BokeCCBaseIE):
    _VALID_URL = r'https?://(?:www\.)?infoq\.com/(?:[^/]+/)+(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'http://www.infoq.com/presentations/A-Few-of-My-Favorite-Python-Things',
        'md5': 'b5ca0e0a8c1fed93b0e65e48e462f9a2',
        'info_dict': {
            'id': 'A-Few-of-My-Favorite-Python-Things',
            'ext': 'mp4',
            'description': 'Mike Pirnat presents some tips and tricks, standard libraries and third party packages that make programming in Python a richer experience.',
            'title': 'A Few of My Favorite [Python] Things',
        },
    }, {
        'url': 'http://www.infoq.com/fr/presentations/changez-avis-sur-javascript',
        'only_matching': True,
    }, {
        'url': 'http://www.infoq.com/cn/presentations/openstack-continued-delivery',
        'md5': '4918d0cca1497f2244572caf626687ef',
        'info_dict': {
            'id': 'openstack-continued-delivery',
            'title': 'OpenStack持续交付之路',
            'ext': 'flv',
            'description': 'md5:308d981fb28fa42f49f9568322c683ff',
        },
        'skip': 'Sorry, the page you visited does not exist',
    }, {
        'url': 'https://www.infoq.com/presentations/Simple-Made-Easy',
        'md5': '0e34642d4d9ef44bf86f66f6399672db',
        'info_dict': {
            'id': 'Simple-Made-Easy',
            'title': 'Simple Made Easy',
            'ext': 'mp3',
            'description': 'md5:3e0e213a8bbd074796ef89ea35ada25b',
        },
        'params': {
            'format': 'bestaudio',
        },
    }]

    def _extract_rtmp_video(self, webpage):
        # The server URL is hardcoded
        video_url = 'rtmpe://videof.infoq.com/cfx/st/'

        # Extract video URL
        encoded_id = self._search_regex(
            r"jsclassref\s*=\s*'([^']*)'", webpage, 'encoded id', default=None)

        real_id = compat_urllib_parse_unquote(compat_b64decode(encoded_id).decode('utf-8'))
        playpath = 'mp4:' + real_id

        return [{
            'format_id': 'rtmp_video',
            'url': video_url,
            'ext': determine_ext(playpath),
            'play_path': playpath,
        }]

    def _extract_cf_auth(self, webpage):
        policy = self._search_regex(r'InfoQConstants\.scp\s*=\s*\'([^\']+)\'', webpage, 'policy')
        signature = self._search_regex(r'InfoQConstants\.scs\s*=\s*\'([^\']+)\'', webpage, 'signature')
        key_pair_id = self._search_regex(r'InfoQConstants\.sck\s*=\s*\'([^\']+)\'', webpage, 'key-pair-id')
        return {
            'Policy': policy,
            'Signature': signature,
            'Key-Pair-Id': key_pair_id,
        }

    def _extract_http_video(self, webpage):
        http_video_url = self._search_regex(r'P\.s\s*=\s*\'([^\']+)\'', webpage, 'video URL')
        http_video_url = update_url_query(http_video_url, self._extract_cf_auth(webpage))
        return [{
            'format_id': 'http_video',
            'url': http_video_url,
            'http_headers': {'Referer': 'https://www.infoq.com/'},
        }]

    def _extract_http_audio(self, webpage, video_id):
        try:
            http_audio_url = traverse_obj(self._form_hidden_inputs('mp3Form', webpage), 'filename')
        except ExtractorError:
            http_audio_url = None
        if not http_audio_url:
            return []

        # base URL is found in the Location header in the response returned by
        # GET https://www.infoq.com/mp3download.action?filename=... when logged in.
        http_audio_url = compat_urlparse.urljoin('http://ress.infoq.com/downloads/mp3downloads/', http_audio_url)
        http_audio_url = update_url_query(http_audio_url, self._extract_cf_auth(webpage))

        # audio file seem to be missing some times even if there is a download link
        # so probe URL to make sure
        if not self._is_valid_url(http_audio_url, video_id):
            return []

        return [{
            'format_id': 'http_audio',
            'url': http_audio_url,
            'vcodec': 'none',
        }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_title = self._html_extract_title(webpage)
        video_description = self._html_search_meta('description', webpage, 'description')

        if '/cn/' in url:
            # for China videos, HTTP video URL exists but always fails with 403
            formats = self._extract_bokecc_formats(webpage, video_id)
        else:
            formats = (
                self._extract_rtmp_video(webpage)
                + self._extract_http_video(webpage)
                + self._extract_http_audio(webpage, video_id))

        return {
            'id': video_id,
            'title': video_title,
            'description': video_description,
            'formats': formats,
        }
