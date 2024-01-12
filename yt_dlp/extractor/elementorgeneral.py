from .common import InfoExtractor
import re
from ..utils import (
    traverse_obj,
    clean_html,
    unescapeHTML,
)


class ElementorGeneralIE(InfoExtractor):
    _VALID_URL = False
    _TESTS = [{
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
        'playlist_mincount': 2,
        'params': {
            'skip_download': True,
        },
    }]

    def _extract_from_webpage(self, url, webpage):
        for element in re.findall(r'<div[^>]+class="[^"]*elementor-widget-(?:video|video-playlist)[^"]*"[^>]*data-settings="([^"]*)"', webpage):
            data_settings = unescapeHTML(clean_html(element))
            data = self._parse_json(data_settings, None, fatal=False)
            tabs = data.get('tabs', [])
            if tabs:  # Handling playlists
                for tab in tabs:
                    video_url = tab.get('youtube_url') or tab.get('vimeo_url') or tab.get('dailymotion_url') or tab.get('videopress_url')
                    if video_url:
                        title = tab.get('title') or self._og_search_title(webpage)
                        thumbnail = tab.get('thumbnail', {}).get('url') or self._og_search_thumbnail(webpage)
                        ie_key = self._get_ie_key(video_url)
                        yield self._build_result(video_url, title, thumbnail, ie_key)
            else:
                video_url = data.get('youtube_url') or data.get('vimeo_url') or data.get('dailymotion_url') or data.get('videopress_url')
                title = data.get('title') or self._og_search_title(webpage)
                thumbnail = traverse_obj(data, ('image_overlay', 'url')) or self._og_search_thumbnail(webpage)
                ie_key = self._get_ie_key(video_url)
                yield self._build_result(video_url, title, thumbnail, ie_key)

    def _get_ie_key(self, url):
        if 'youtube' in url or 'youtu.be' in url:
            return 'Youtube'
        elif 'vimeo' in url:
            return 'Vimeo'
        elif 'dailymotion' in url:
            return 'Dailymotion'
        elif 'videopress' in url:
            return 'Videopress'
        return 'Generic'

    def _build_result(self, video_url, title, thumbnail, ie_key):
        return {
            'id': video_url,
            'title': title,
            '_type': 'url_transparent',
            'url': video_url,
            'thumbnail': thumbnail,
            'ie_key': ie_key,
        }
