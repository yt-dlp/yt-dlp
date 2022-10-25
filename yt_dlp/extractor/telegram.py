import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    parse_duration,
    traverse_obj,
    unified_timestamp,
    update_url_query,
    url_basename,
)


class TelegramEmbedIE(InfoExtractor):
    IE_NAME = 'telegram:embed'
    _VALID_URL = r'https?://t\.me/(?P<uploader>[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://t.me/europa_press/613',
        'md5': 'dd707708aea958c11a590e8068825f22',
        'info_dict': {
            'id': '613',
            'ext': 'mp4',
            'title': 'Europa Press ✔',
            'description': 'md5:6ce2d7e8d56eda16d80607b23db7b252',
            'uploader': 'europa_press',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1635631203,
            'upload_date': '20211030',
            'duration': 61,
        },
    }, {
        # 2-video post
        'url': 'https://t.me/vorposte/29342',
        'info_dict': {
            'id': 'vorposte-29342',
            'title': 'Форпост 29342',
            'description': 'md5:4d573fd641c3a21f58ad6bb5f16fe526',
        },
        'playlist_count': 2,
        'params': {
            'skip_download': True,
        },
    }, {
        # 2-video post with --no-playlist
        'url': 'https://t.me/vorposte/29343',
        'md5': '1724e96053c18e788c8464038876e245',
        'info_dict': {
            'id': '29343',
            'ext': 'mp4',
            'title': 'Форпост',
            'uploader': 'vorposte',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1666384480,
            'upload_date': '20221021',
            'duration': 35,
        },
        'params': {
            'noplaylist': True,
        }
    }, {
        # 2-video post with 'single' query param
        'url': 'https://t.me/vorposte/29342?single',
        'md5': 'd20b202f1e41400a9f43201428add18f',
        'info_dict': {
            'id': '29342',
            'ext': 'mp4',
            'title': 'Форпост',
            'description': 'md5:4d573fd641c3a21f58ad6bb5f16fe526',
            'uploader': 'vorposte',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1666384480,
            'upload_date': '20221021',
            'duration': 33,
        },
    }, {
        # 2-video post with 'single' query param and --yes-playlist
        'url': 'https://t.me/vorposte/29343?single',
        'info_dict': {
            'id': 'vorposte-29343',
            'title': 'Форпост 29343',
            'description': 'md5:4d573fd641c3a21f58ad6bb5f16fe526',
        },
        'playlist_count': 2,
        'params': {
            'noplaylist': False,
            'skip_download': True,
        }
    }]

    def _real_extract(self, url):
        uploader, msg_id = self._match_valid_url(url).group('uploader', 'id')

        query = {'embed': '1'}
        if self.get_param('noplaylist'):
            query['single'] = True
        elif self.get_param('noplaylist') is False:
            pass
        elif '?single' in url:  # param 'noplaylist' is None
            query['single'] = True
        url = update_url_query(url, {'single': []})  # strip 'single' from original URL query
        embed = self._download_webpage(url, msg_id, query=query, note='Downloading embed frame')

        message = {
            'title': clean_html(get_element_by_class('tgme_widget_message_author', embed)),
            'description': clean_html(get_element_by_class('tgme_widget_message_text', embed)),
            'uploader': uploader,
            'timestamp': unified_timestamp(self._search_regex(
                r'<time[^>]*datetime="([^"]*)"', embed, 'timestamp', fatal=False)),
        }

        videos = []
        for video in re.findall(r'<a class="tgme_widget_message_video_player(?s:.+?)</time>', embed):
            video_url = self._search_regex(
                r'<video[^>]+src="([^"]+)"', video, 'video URL', fatal=False)
            webpage_url = self._search_regex(
                r'<a class="tgme_widget_message_video_player[^>]+href="([^"]+)"',
                video, 'webpage URL', fatal=False)
            if not video_url or not webpage_url:
                continue
            formats = [{
                'url': video_url,
                'ext': 'mp4',
            }]
            self._sort_formats(formats)
            videos.append({
                'id': url_basename(webpage_url),
                'duration': parse_duration(self._search_regex(
                    r'<time[^>]+duration[^>]*>([\d:]+)</time>', video, 'duration', fatal=False)),
                'thumbnail': self._search_regex(
                    r'tgme_widget_message_video_thumb"[^>]+background-image:url\(\'([^\']+)\'\)',
                    video, 'thumbnail', fatal=False),
                'formats': formats,
                **message,
            })

        if query.get('single') or len(videos) < 2:
            return traverse_obj(videos, lambda _, x: x['id'] == msg_id, get_all=False)
        else:
            return self.playlist_result(
                videos, f'{uploader}-{msg_id}', f'{message["title"]} {msg_id}', message['description'])
