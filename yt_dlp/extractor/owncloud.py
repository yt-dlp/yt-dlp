import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    url_or_none,
    urlencode_postdata,
)


class OwnCloudIE(InfoExtractor):
    _INSTANCES_RE = '|'.join((
        r'(?:[^\.]+\.)?sciebo\.de',
        r'cloud\.uni-koblenz-landau\.de',
    ))
    _VALID_URL = rf'https?://(?:{_INSTANCES_RE})/s/(?P<id>[\w.-]+)'

    _TESTS = [
        {
            'url': 'https://ruhr-uni-bochum.sciebo.de/s/wWhqZzh9jTumVFN',
            'info_dict': {
                'id': 'wWhqZzh9jTumVFN',
                'ext': 'mp4',
                'title': 'CmvpJST.mp4',
            },
        },
        {
            'url': 'https://ruhr-uni-bochum.sciebo.de/s/WNDuFu0XuFtmm3f',
            'info_dict': {
                'id': 'WNDuFu0XuFtmm3f',
                'ext': 'mp4',
                'title': 'CmvpJST.mp4',
            },
            'params': {
                'videopassword': '12345',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, video_id)

        if re.search(r'<label[^>]+for="password"', webpage):
            webpage = self._verify_video_password(webpage, urlh.url, video_id)

        hidden_inputs = self._hidden_inputs(webpage)
        title = hidden_inputs.get('filename')
        parsed_url = urllib.parse.urlparse(url)

        return {
            'id': video_id,
            'title': title,
            'url': url_or_none(hidden_inputs.get('downloadURL')) or parsed_url._replace(
                path=urllib.parse.urljoin(parsed_url.path, 'download')).geturl(),
            'ext': determine_ext(title),
        }

    def _verify_video_password(self, webpage, url, video_id):
        password = self.get_param('videopassword')
        if password is None:
            raise ExtractorError(
                'This video is protected by a password, use the --video-password option',
                expected=True)

        validation_response = self._download_webpage(
            url, video_id, 'Validating Password', 'Wrong password?',
            data=urlencode_postdata({
                'requesttoken': self._hidden_inputs(webpage)['requesttoken'],
                'password': password,
            }))

        if re.search(r'<label[^>]+for="password"', validation_response):
            warning = self._search_regex(
                r'<div[^>]+class="warning">([^<]*)</div>', validation_response,
                'warning', default='The password is wrong')
            raise ExtractorError(f'Opening the video failed, {self.IE_NAME} said: {warning!r}', expected=True)
        return validation_response
