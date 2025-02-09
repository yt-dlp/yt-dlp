import re

from .common import InfoExtractor
from .vimeo import VimeoIE
from .youtube import YoutubeIE
from ..utils import unescapeHTML, url_or_none
from ..utils.traversal import traverse_obj


class ElementorEmbedIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        'url': 'https://capitaltv.cy/2023/12/14/υγεια-και-ζωη-14-12-2023-δρ-ξενια-κωσταντινιδο/',
        'info_dict': {
            'id': 'KgzuxwuQwM4',
            'ext': 'mp4',
            'title': 'ΥΓΕΙΑ ΚΑΙ ΖΩΗ 14 12 2023 ΔΡ  ΞΕΝΙΑ ΚΩΣΤΑΝΤΙΝΙΔΟΥ',
            'thumbnail': 'https://i.ytimg.com/vi/KgzuxwuQwM4/maxresdefault.jpg',
            'playable_in_embed': True,
            'tags': 'count:16',
            'like_count': int,
            'channel': 'Capital TV Cyprus',
            'channel_id': 'UCR8LwVKTLGEXt4ZAErpCMrg',
            'availability': 'public',
            'description': 'md5:7a3308a22881aea4612358c4ba121f77',
            'duration': 2891,
            'upload_date': '20231214',
            'uploader_id': '@capitaltvcyprus6389',
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UCR8LwVKTLGEXt4ZAErpCMrg',
            'uploader_url': 'https://www.youtube.com/@capitaltvcyprus6389',
            'uploader': 'Capital TV Cyprus',
            'age_limit': 0,
            'categories': ['News & Politics'],
            'view_count': int,
            'channel_follower_count': int,
        },
    }, {
        'url': 'https://elementor.com/academy/theme-builder-collection/?playlist=76011151&video=9e59909',
        'info_dict': {
            'id': '?playlist=76011151&video=9e59909',
            'title': 'Theme Builder Collection - Academy',
            'age_limit': 0,
            'timestamp': 1702196984.0,
            'upload_date': '20231210',
            'description': 'md5:7f52c52715ee9e54fd7f82210511673d',
            'thumbnail': 'https://elementor.com/academy/wp-content/uploads/2021/07/Theme-Builder-1.png',
        },
        'playlist_count': 11,
        'params': {
            'skip_download': True,
        },
    }]
    _WIDGET_REGEX = r'<div[^>]+class="[^"]*elementor-widget-video(?:-playlist)?[^"]*"[^>]*data-settings="([^"]*)"'

    def _extract_from_webpage(self, url, webpage):
        for data_settings in re.findall(self._WIDGET_REGEX, webpage):
            data = self._parse_json(data_settings, None, fatal=False, transform_source=unescapeHTML)
            if youtube_url := traverse_obj(data, ('youtube_url', {url_or_none})):
                yield self.url_result(youtube_url, ie=YoutubeIE)

            for video in traverse_obj(data, ('tabs', lambda _, v: v['_id'], {dict})):
                if youtube_url := traverse_obj(video, ('youtube_url', {url_or_none})):
                    yield self.url_result(youtube_url, ie=YoutubeIE)
                if vimeo_url := traverse_obj(video, ('vimeo_url', {url_or_none})):
                    yield self.url_result(vimeo_url, ie=VimeoIE)
                for direct_url in traverse_obj(video, (('hosted_url', 'external_url'), 'url', {url_or_none})):
                    yield {
                        'id': video['_id'],
                        'url': direct_url,
                        'title': video.get('title'),
                    }
