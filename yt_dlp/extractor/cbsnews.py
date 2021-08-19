# coding: utf-8
from __future__ import unicode_literals

import re
import zlib

from .common import InfoExtractor
from .cbs import CBSIE
from ..compat import (
    compat_b64decode,
    compat_urllib_parse_unquote,
)
from ..utils import (
    parse_duration,
)


class CBSNewsEmbedIE(CBSIE):
    IE_NAME = 'cbsnews:embed'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/embed/video[^#]*#(?P<id>.+)'
    _TESTS = [{
        'url': 'https://www.cbsnews.com/embed/video/?v=1.c9b5b61492913d6660db0b2f03579ef25e86307a#1Vb7b9s2EP5XBAHbT6Gt98PAMKTJ0se6LVjWYWtdGBR1stlIpEBSTtwi%2F%2FvuJNkNhmHdGxgM2NL57vjd6zt%2B8PngdN%2Fyg79qeGvhzN%2FLGrS%2F%2BuBLB531V28%2B%2BO7Qg7%2Fy97r2z3xZ42NW8yLhDbA0S0KWlHnIijwKWJBHZZnHBa8Cgbpdf%2F89NM9Hi9fXifhpr8sr%2FlP848tn%2BTdXycX25zh4cdX%2FvHl6PmmPqnWQv9w8Ed%2B9GjYRim07bFEqdG%2BZVHuwTm65A7bVRrYtR5lAyMox7pigF6W4k%2By91mjspGsJ%2BwVae4%2BsvdnaO1p73HkXs%2FVisUDTGm7R8IcdnOROeq%2B19qT1amhA1VJtPenoTUgrtfKc9m7Rq8dP7nnjwOB7wg7ADdNt7VX64DWAWlKhPtmDEq22g4GF99x6Dk9E8OSsankHXqPNKDxC%2FdK7MLKTircTDgsI3mmj4OBdSq64dy7fd1x577RU1rt4cvMtOaulFYOd%2FLewRWvDO9lIgXFpZSnkZmjbv5SxKTPoQXClFbpsf%2Fhbbpzs0IB3vb8KkyzJQ%2BywOAgCrMpgRrz%2BKk4fvb7kFbR4XJCu0gAdtNO7woCwZTu%2BBUs9bam%2Fds71drVerpeisgrubLjAB4nnOSkWQnfr5W6o1ku5Xpr1MgrCbL0M0vUyDtfLLK15WiYp47xKWSLyjFVpwVmVJSLIoCjSOFkv3W7oKsVliwZJcB9nwXpZ5GEQQwY8jNKqKCBrgjTLeFxgdCIpazojDgnRtn43J6kG7nZ6cAbxh0EeFFk4%2B1u867cY5u4344n%2FxXjCqAjucdTHgLKojNKmSfO8KRsOFY%2FzKEYCKEJBzv90QA9nfm9gL%2BHulaFqUkz9ULUYxl62B3U%2FRVNLA8IhggaPycOoBuwOCESciDQVSSUgiOMsROB%2FhKfwCKOzEk%2B4k6rWd4uuT%2FwTDz7K7t3d3WLO8ISD95jSPQbayBacthbz86XVgxHwhex5zawzgDOmtp%2F3GPcXn0VXHdSS029%2Fj99UC%2FwJUvyKQ%2FzKyixIEVlYJOn4RxxuaH43Ty9fbJ5OObykHH435XAzJTHeOF4hhEUXD8URe%2FQ%2FBT%2BMpf8d5GN02Ox%2FfiGsl7TA7POu1xZ5%2BbTzcAVKMe48mqcC21hkacVEVScM26liVVBnrKkC4CLKyzAvHu0lhEaTKMFwI3a4SN9MsrfYzdBLq2vkwRD1gVviLT8kY9h2CHH6Y%2Bix6609weFtey4ESp60WtyeWMy%2BsmBuhsoKIyuoT%2Bq2R%2FrW5qi3g%2FvzS2j40DoixDP8%2BKP0yUdpXJ4l6Vla%2Bg9vce%2BC4yM5YlUcbA%2F0jLKdpmTwvsdN5z88nAIe08%2F0HgxeG1iv%2B6Hlhjh7uiW0SDzYNI92L401uha3JKYk268UVRzdOzNQvAaJqoXzAc80dAV440NZ1WVVAAMRYQ2KrGJFmDUsq8saWSnjvIj8t78y%2FRa3JRnbHVfyFpfwoDiGpPgjzekyUiKNlU3OMlwuLMmzgvEojllYVE2Z1HhImvsnk%2BuhusTEoB21PAtSFodeFK3iYhXEH9WOG2%2FkOE833sfeG%2Ff5cfHtEFNXgYes0%2FXj7aGivUgJ9XpusCtoNcNYVVnJVrrDo0OmJAutHCpuZul4W9lLcfy7BnuLPT02%2ByXsCTk%2B9zhzswIN04YueNSK%2BPtM0jS88QdLqSLJDTLsuGZJNolm2yO0PXh3UPnz9Ix5bfIAqxPjvETQsDCEiPG4QbqNyhBZISxybLnZYCrW5H3Axp690%2F0BJdXtDZ5ITuM4xj3f4oUHGzc5JeJmZKpp%2FjwKh4wMV%2FV1yx3emLoR0MwbG4K%2F%2BZgVep3PnzXGDHZ6a3i%2Fk%2BJrONDN13%2Bnq6tBTYk4o7cLGhBtqCC4KwacGHpEVuoH5JNro%2FE6JfE6d5RydbiR76k%2BW5wioDHBIjw1euhHjUGRB0y5A97KoaPx6MlL%2BwgboUVtUFRI%2FLemgTpdtF59ii7pab08kuPcfWzs0l%2FRI5takWnFpka0zOgWRtYcuf9aIxZMxlwr6IiGpsb6j2DQUXPl%2FimXI599Ev7fWjoPD78A',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        item = self._parse_json(zlib.decompress(compat_b64decode(
            compat_urllib_parse_unquote(self._match_id(url))),
            -zlib.MAX_WBITS).decode('utf-8'), None)['video']['items'][0]
        return self._extract_video_info(item['mpxRefId'], 'cbsnews')


class CBSNewsIE(CBSIE):
    IE_NAME = 'cbsnews'
    IE_DESC = 'CBS News'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/(?:news|video)/(?P<id>[\da-z_-]+)'

    _TESTS = [
        {
            # 60 minutes
            'url': 'http://www.cbsnews.com/news/artificial-intelligence-positioned-to-be-a-game-changer/',
            'info_dict': {
                'id': 'Y_nf_aEg6WwO9OLAq0MpKaPgfnBUxfW4',
                'ext': 'flv',
                'title': 'Artificial Intelligence, real-life applications',
                'description': 'md5:a7aaf27f1b4777244de8b0b442289304',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 317,
                'uploader': 'CBSI-NEW',
                'timestamp': 1476046464,
                'upload_date': '20161009',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.cbsnews.com/video/fort-hood-shooting-army-downplays-mental-illness-as-cause-of-attack/',
            'info_dict': {
                'id': 'SNJBOYzXiWBOvaLsdzwH8fmtP1SCd91Y',
                'ext': 'mp4',
                'title': 'Fort Hood shooting: Army downplays mental illness as cause of attack',
                'description': 'md5:4a6983e480542d8b333a947bfc64ddc7',
                'upload_date': '20140404',
                'timestamp': 1396650660,
                'uploader': 'CBSI-NEW',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 205,
                'subtitles': {
                    'en': [{
                        'ext': 'ttml',
                    }],
                },
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            # 48 hours
            'url': 'http://www.cbsnews.com/news/maria-ridulph-murder-will-the-nations-oldest-cold-case-to-go-to-trial-ever-get-solved/',
            'info_dict': {
                'title': 'Cold as Ice',
                'description': 'Can a childhood memory solve the 1957 murder of 7-year-old Maria Ridulph?',
            },
            'playlist_mincount': 7,
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        entries = []
        for embed_url in re.findall(r'<iframe[^>]+data-src="(https?://(?:www\.)?cbsnews\.com/embed/video/[^#]*#[^"]+)"', webpage):
            entries.append(self.url_result(embed_url, CBSNewsEmbedIE.ie_key()))
        if entries:
            return self.playlist_result(
                entries, playlist_title=self._html_search_meta(['og:title', 'twitter:title'], webpage),
                playlist_description=self._html_search_meta(['og:description', 'twitter:description', 'description'], webpage))

        item = self._parse_json(self._html_search_regex(
            r'CBSNEWS\.defaultPayload\s*=\s*({.+})',
            webpage, 'video JSON info'), display_id)['items'][0]
        return self._extract_video_info(item['mpxRefId'], 'cbsnews')


class CBSNewsLiveVideoIE(InfoExtractor):
    IE_NAME = 'cbsnews:livevideo'
    IE_DESC = 'CBS News Live Videos'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/live/video/(?P<id>[^/?#]+)'

    # Live videos get deleted soon. See http://www.cbsnews.com/live/ for the latest examples
    _TEST = {
        'url': 'http://www.cbsnews.com/live/video/clinton-sanders-prepare-to-face-off-in-nh/',
        'info_dict': {
            'id': 'clinton-sanders-prepare-to-face-off-in-nh',
            'ext': 'mp4',
            'title': 'Clinton, Sanders Prepare To Face Off In NH',
            'duration': 334,
        },
        'skip': 'Video gone',
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        video_info = self._download_json(
            'http://feeds.cbsn.cbsnews.com/rundown/story', display_id, query={
                'device': 'desktop',
                'dvr_slug': display_id,
            })

        formats = self._extract_akamai_formats(video_info['url'], display_id)
        self._sort_formats(formats)

        return {
            'id': display_id,
            'display_id': display_id,
            'title': video_info['headline'],
            'thumbnail': video_info.get('thumbnail_url_hd') or video_info.get('thumbnail_url_sd'),
            'duration': parse_duration(video_info.get('segmentDur')),
            'formats': formats,
        }
