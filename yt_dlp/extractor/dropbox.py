import os.path
import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    ExtractorError,
    traverse_obj,
    try_get,
    url_basename,
)


class DropboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dropbox[.]com/sh?/(?P<id>[a-zA-Z0-9]{15})/.*'
    _TESTS = [
        {
            'url': 'https://www.dropbox.com/s/nelirfsxnmcfbfh/youtube-dl%20test%20video%20%27%C3%A4%22BaW_jenozKc.mp4?dl=0',
            'info_dict': {
                'id': 'nelirfsxnmcfbfh',
                'ext': 'mp4',
                'title': 'youtube-dl test video \'ä"BaW_jenozKc'
            }
        }, {
            'url': 'https://www.dropbox.com/sh/662glsejgzoj9sr/AAByil3FGH9KFNZ13e08eSa1a/Pregame%20Ceremony%20Program%20PA%2020140518.m4v',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        webpage = self._download_webpage(url, video_id)
        fn = compat_urllib_parse_unquote(url_basename(url))
        title = os.path.splitext(fn)[0]

        password = self.get_param('videopassword')
        if (self._og_search_title(webpage) == 'Dropbox - Password Required'
                or 'Enter the password for this link' in webpage):

            if password:
                content_id = self._search_regex(r'content_id=(.*?)["\']', webpage, 'content_id')
                payload = f'is_xhr=true&t={self._get_cookies("https://www.dropbox.com").get("t").value}&content_id={content_id}&password={password}&url={url}'
                response = self._download_json(
                    'https://www.dropbox.com/sm/auth', video_id, 'POSTing video password', data=payload.encode('UTF-8'),
                    headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})

                if response.get('status') != 'authed':
                    raise ExtractorError('Authentication failed!', expected=True)
                webpage = self._download_webpage(url, video_id)
            elif self._get_cookies('https://dropbox.com').get('sm_auth'):
                webpage = self._download_webpage(url, video_id)
            else:
                raise ExtractorError('Password protected video, use --video-password <password>', expected=True)

        json_string = self._html_search_regex(r'InitReact\.mountComponent\(.*?,\s*(\{.+\})\s*?\)', webpage, 'Info JSON')
        info_json = self._parse_json(json_string, video_id).get('props')
        transcode_url = traverse_obj(info_json, ((None, 'preview'), 'file', 'preview', 'content', 'transcode_url'), get_all=False)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(transcode_url, video_id)

        # downloads enabled we can get the original file
        if 'anonymous' in (try_get(info_json, lambda x: x['sharePermission']['canDownloadRoles']) or []):
            video_url = re.sub(r'[?&]dl=0', '', url)
            video_url += ('?' if '?' not in video_url else '&') + 'dl=1'
            formats.append({'url': video_url, 'format_id': 'original', 'format_note': 'Original', 'quality': 1})
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles
        }
