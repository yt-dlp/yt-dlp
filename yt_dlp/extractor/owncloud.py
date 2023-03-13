import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    url_or_none,
    urlencode_postdata,
)


class OwnCloudIE(InfoExtractor):
    IE_NAME = 'owncloud'

    _INSTANCES_RE = r'''(?:
                            (?:[^\.]+\.)?sciebo\.de|
                            cloud\.uni-koblenz-landau\.de|
                        )'''
    _VALID_URL = rf'''(?x)
            (?P<server>https?://{_INSTANCES_RE})/s/
            (?P<id>[\w\-\.]+)
            (?P<extra>/.*)?
        '''

    _TESTS = [
        {
            'url': 'https://ruhr-uni-bochum.sciebo.de/s/wWhqZzh9jTumVFN',
            'info_dict': {
                'id': 'wWhqZzh9jTumVFN',
                'ext': 'mp4',
                'title': 'CmvpJST.mp4',
            },
        },
    ]

    def _real_extract(self, url):
        server, video_id = self._match_valid_url(url).group('server', 'id')

        webpage, urlh = self._download_webpage_handle(url, f'{server}/s/{video_id}', 'Downloading webpage')

        if self._search_regex(
            r'<label[^>]+?for="(password)"', webpage, 'password field', fatal=False, default=None
        ):
            # Password protected
            webpage, urlh = self._verify_video_password(webpage, urlh.geturl(), video_id)

        hidden_inputs = self._hidden_inputs(webpage)
        title = hidden_inputs.get('filename')

        return {
            'id': video_id,
            'title': title,
            'formats': [
                {
                    'url': url_or_none(hidden_inputs.get('downloadURL') or self._extend_to_download_url(urlh.geturl())),
                    'ext': determine_ext(title),
                    'filesize': int_or_none(hidden_inputs.get('filesize')),
                }
            ],
        }

    def _extend_to_download_url(self, url: str) -> str:
        # Adds /download to the end of the URL path
        url_parts = list(urllib.parse.urlparse(url))
        url_parts[2] = url_parts[2].rstrip('/') + '/download'
        return urllib.parse.urlunparse(url_parts)

    def _verify_video_password(self, webpage, url, video_id):
        password = self._downloader.params.get('videopassword')
        if password is None:
            raise ExtractorError(
                'This video is protected by a password, use the --video-password option',
                expected=True
            )

        data = urlencode_postdata(
            {
                'requesttoken': self._search_regex(
                    r'<input[^>]+?name="requesttoken" value="([^\"]+)"', webpage, 'requesttoken'
                ),
                'password': password,
            }
        )

        validation_response, urlh = self._download_webpage_handle(
            url, video_id, note='Validating Password...', errnote='Wrong password?', data=data
        )

        if self._search_regex(
            r'<label[^>]+?for="(password)"', validation_response, 'password field', fatal=False, default=None
        ):
            # Still password protected
            warning = self._search_regex(
                r'<div[^>]+?class="warning">([^<]*)</div>', validation_response, 'warning',
                fatal=False, default="The password is wrong. Try again.",
            )
            raise ExtractorError(f'Login failed, {self.IE_NAME} said: {warning!r}', expected=True)
        return validation_response, urlh
