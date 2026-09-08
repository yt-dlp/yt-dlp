import json
import re
import uuid

from .common import InfoExtractor
from ..utils import ExtractorError


class CeskaTelevizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ceskatelevize\.cz/porady/(?P<show_id>\d+-[^/]+)/(?P<id>\d+)'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        # 1. Fetch the webpage to extract metadata
        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage, default=None)
        if not title:
            title = self._html_search_regex(r'<title>(.*?)</title>', webpage, 'title', default=video_id)
            title = title.split('|')[0].strip()

        thumbnail = self._og_search_thumbnail(webpage)
        description = self._og_search_description(webpage, default=None)

        # 2. Query the new API Endpoint
        device_id = str(uuid.uuid4())
        api_url = (
            f'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/'
            f'media/external/{video_id}?canPlayDrm=true&quality=web&streamType=dash'
            f'&deviceId={device_id}&origin=ivysilani&client=iVysilaniWeb&clientVersion=0.37.8'
        )

        api_data = self._download_json(api_url, video_id, headers={
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0',
        })

        formats = []
        subtitles = {}

        # 3. Parse JSON to find stream and subtitle URLs
        raw_json = json.dumps(api_data).replace('\\/', '/')

        stream_match = re.search(r'"(https://[^"]+(?:token=[^"]+|mpd[^"]*))"', raw_json)
        if stream_match:
            stream_url = stream_match.group(1).replace('\\/', '/')

            # yt-dlp's built-in DASH extractor automatically gets the fragments
            formats, subs = self._extract_mpd_formats_and_subtitles(
                stream_url, video_id, mpd_id='dash', fatal=False)
            self._merge_subtitles(subs, target=subtitles)
        else:
            raise ExtractorError('Could not find stream URL. Video may be DRM protected.', expected=True)

        sub_match = re.search(r'"(https://[^"]+\.vtt[^"]*)"', raw_json)
        if sub_match:
            sub_url = sub_match.group(1).replace('\\/', '/')
            subtitles.setdefault('cs', []).append({
                'url': sub_url,
                'ext': 'vtt',
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': subtitles,
        }
