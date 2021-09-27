# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import remove_start


class TeleMBIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?telemb\.be/(?P<display_id>.+?)_d_(?P<id>\d+)\.html'
    _TESTS = [
        {
            'url': 'http://www.telemb.be/mons-cook-with-danielle-des-cours-de-cuisine-en-anglais-_d_13466.html',
            'md5': 'f45ea69878516ba039835794e0f8f783',
            'info_dict': {
                'id': '13466',
                'display_id': 'mons-cook-with-danielle-des-cours-de-cuisine-en-anglais-',
                'ext': 'mp4',
                'title': 'Mons - Cook with Danielle : des cours de cuisine en anglais ! - Les reportages',
                'description': 'md5:bc5225f47b17c309761c856ad4776265',
                'thumbnail': r're:^http://.*\.(?:jpg|png)$',
            }
        },
        {
            # non-ASCII characters in download URL
            'url': 'http://telemb.be/les-reportages-havre-incendie-mortel_d_13514.html',
            'md5': '6e9682736e5ccd4eab7f21e855350733',
            'info_dict': {
                'id': '13514',
                'display_id': 'les-reportages-havre-incendie-mortel',
                'ext': 'mp4',
                'title': 'Havré - Incendie mortel - Les reportages',
                'description': 'md5:5e54cb449acb029c2b7734e2d946bd4a',
                'thumbnail': r're:^http://.*\.(?:jpg|png)$',
            }
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        formats = []
        for video_url in re.findall(r'file\s*:\s*"([^"]+)"', webpage):
            fmt = {
                'url': video_url,
                'format_id': video_url.split(':')[0]
            }
            rtmp = re.search(r'^(?P<url>rtmp://[^/]+/(?P<app>.+))/(?P<playpath>mp4:.+)$', video_url)
            if rtmp:
                fmt.update({
                    'play_path': rtmp.group('playpath'),
                    'app': rtmp.group('app'),
                    'player_url': 'http://p.jwpcdn.com/6/10/jwplayer.flash.swf',
                    'page_url': 'http://www.telemb.be',
                    'preference': -10,
                })
            formats.append(fmt)
        self._sort_formats(formats)

        title = remove_start(self._og_search_title(webpage), 'TéléMB : ')
        description = self._html_search_regex(
            r'<meta property="og:description" content="(.+?)" />',
            webpage, 'description', fatal=False)
        thumbnail = self._og_search_thumbnail(webpage)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }
