import base64
import os.path
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    update_url_query,
    url_basename,
)


class DropboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dropbox\.com/(?:(?:e/)?scl/fi|sh?)/(?P<id>\w+)'
    _TESTS = [
        {
            'url': 'https://www.dropbox.com/s/nelirfsxnmcfbfh/youtube-dl%20test%20video%20%27%C3%A4%22BaW_jenozKc.mp4?dl=0',
            'info_dict': {
                'id': 'nelirfsxnmcfbfh',
                'ext': 'mp4',
                'title': 'youtube-dl test video \'ä"BaW_jenozKc',
            },
        }, {
            'url': 'https://www.dropbox.com/s/nelirfsxnmcfbfh',
            'only_matching': True,
        }, {
            'url': 'https://www.dropbox.com/sh/2mgpiuq7kv8nqdf/AABy-fW4dkydT4GmWi2mdOUDa?dl=0&preview=Drone+Shot.mp4',
            'only_matching': True,
        }, {
            'url': 'https://www.dropbox.com/scl/fi/r2kd2skcy5ylbbta5y1pz/DJI_0003.MP4?dl=0&rlkey=wcdgqangn7t3lnmmv6li9mu9h',
            'only_matching': True,
        }, {
            'url': 'https://www.dropbox.com/e/scl/fi/r2kd2skcy5ylbbta5y1pz/DJI_0003.MP4?dl=0&rlkey=wcdgqangn7t3lnmmv6li9mu9h',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        webpage = self._download_webpage(url, video_id)
        fn = urllib.parse.unquote(url_basename(url))
        title = os.path.splitext(fn)[0]

        password = self.get_param('videopassword')
        if (self._og_search_title(webpage) == 'Dropbox - Password Required'
                or 'Enter the password for this link' in webpage):

            if password:
                content_id = self._search_regex(r'content_id=(.*?)["\']', webpage, 'content_id')
                payload = f'is_xhr=true&t={self._get_cookies("https://www.dropbox.com").get("t").value}&content_id={content_id}&password={password}&url={url}'
                response = self._download_json(
                    'https://www.dropbox.com/sm/auth', video_id, 'POSTing video password', data=payload.encode(),
                    headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})

                if response.get('status') != 'authed':
                    raise ExtractorError('Authentication failed!', expected=True)
                webpage = self._download_webpage(url, video_id)
            elif self._get_cookies('https://dropbox.com').get('sm_auth'):
                webpage = self._download_webpage(url, video_id)
            else:
                raise ExtractorError('Password protected video, use --video-password <password>', expected=True)

        formats, subtitles, has_anonymous_download = [], {}, False
        for encoded in reversed(re.findall(r'registerStreamedPrefetch\s*\(\s*"[\w/+=]+"\s*,\s*"([\w/+=]+)"', webpage)):
            decoded = base64.b64decode(encoded).decode('utf-8', 'ignore')
            if not has_anonymous_download:
                has_anonymous_download = self._search_regex(
                    r'(anonymous:\tanonymous)', decoded, 'anonymous', default=False)
            transcode_url = self._search_regex(
                r'\n.(https://[^\x03\x08\x12\n]+\.m3u8)', decoded, 'transcode url', default=None)
            if not transcode_url:
                continue
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(transcode_url, video_id, 'mp4')
            break

        # downloads enabled we can get the original file
        if has_anonymous_download:
            formats.append({
                'url': update_url_query(url, {'dl': '1'}),
                'format_id': 'original',
                'format_note': 'Original',
                'quality': 1,
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
        }
