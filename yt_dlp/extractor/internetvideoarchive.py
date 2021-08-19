from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)


class InternetVideoArchiveIE(InfoExtractor):
    _VALID_URL = r'https?://video\.internetvideoarchive\.net/(?:player|flash/players)/.*?\?.*?publishedid.*?'

    _TEST = {
        'url': 'http://video.internetvideoarchive.net/player/6/configuration.ashx?customerid=69249&publishedid=194487&reporttag=vdbetatitle&playerid=641&autolist=0&domain=www.videodetective.com&maxrate=high&minrate=low&socialplayer=false',
        'info_dict': {
            'id': '194487',
            'ext': 'mp4',
            'title': 'Kick-Ass 2',
            'description': 'md5:c189d5b7280400630a1d3dd17eaa8d8a',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    @staticmethod
    def _build_json_url(query):
        return 'http://video.internetvideoarchive.net/player/6/configuration.ashx?' + query

    def _real_extract(self, url):
        query = compat_parse_qs(compat_urlparse.urlparse(url).query)
        video_id = query['publishedid'][0]
        data = self._download_json(
            'https://video.internetvideoarchive.net/videojs7/videojs7.ivasettings.ashx',
            video_id, data=json.dumps({
                'customerid': query['customerid'][0],
                'publishedid': video_id,
            }).encode())
        title = data['Title']
        formats = self._extract_m3u8_formats(
            data['VideoUrl'], video_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False)
        file_url = formats[0]['url']
        if '.ism/' in file_url:
            replace_url = lambda x: re.sub(r'\.ism/[^?]+', '.ism/' + x, file_url)
            formats.extend(self._extract_f4m_formats(
                replace_url('.f4m'), video_id, f4m_id='hds', fatal=False))
            formats.extend(self._extract_mpd_formats(
                replace_url('.mpd'), video_id, mpd_id='dash', fatal=False))
            formats.extend(self._extract_ism_formats(
                replace_url('Manifest'), video_id, ism_id='mss', fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': data.get('PosterUrl'),
            'description': data.get('Description'),
        }
