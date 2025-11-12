import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    format_field,
    get_element_by_class,
    parse_duration,
    parse_qs,
    traverse_obj,
    unified_timestamp,
    update_url_query,
    url_basename,
)


class TelegramEmbedIE(InfoExtractor):
    IE_NAME = 'telegram:embed'
    _VALID_URL = r'https?://t\.me/(?P<channel_id>[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://t.me/europa_press/613',
        'md5': 'dd707708aea958c11a590e8068825f22',
        'info_dict': {
            'id': '613',
            'ext': 'mp4',
            'title': 'md5:6ce2d7e8d56eda16d80607b23db7b252',
            'description': 'md5:6ce2d7e8d56eda16d80607b23db7b252',
            'channel_id': 'europa_press',
            'channel': 'Europa Press ✔',
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
            'description': 'md5:9d92e22169a3e136d5d69df25f82c3dc',
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
            'title': 'md5:9d92e22169a3e136d5d69df25f82c3dc',
            'description': 'md5:9d92e22169a3e136d5d69df25f82c3dc',
            'channel_id': 'vorposte',
            'channel': 'Форпост',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1666384480,
            'upload_date': '20221021',
            'duration': 35,
        },
        'params': {
            'noplaylist': True,
        },
    }, {
        # 2-video post with 'single' query param
        'url': 'https://t.me/vorposte/29342?single',
        'md5': 'd20b202f1e41400a9f43201428add18f',
        'info_dict': {
            'id': '29342',
            'ext': 'mp4',
            'title': 'md5:9d92e22169a3e136d5d69df25f82c3dc',
            'description': 'md5:9d92e22169a3e136d5d69df25f82c3dc',
            'channel_id': 'vorposte',
            'channel': 'Форпост',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1666384480,
            'upload_date': '20221021',
            'duration': 33,
        },
    }]

    def _real_extract(self, url):
        channel_id, msg_id = self._match_valid_url(url).group('channel_id', 'id')
        embed = self._download_webpage(
            url, msg_id, query={'embed': '1', 'single': []}, note='Downloading embed frame')

        def clean_text(html_class, html):
            text = clean_html(get_element_by_class(html_class, html))
            return text.replace('\n', ' ') if text else None

        description = clean_text('tgme_widget_message_text', embed)
        message = {
            'title': description or '',
            'description': description,
            'channel': clean_text('tgme_widget_message_author', embed),
            'channel_id': channel_id,
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
            videos.append({
                'id': url_basename(webpage_url),
                'webpage_url': update_url_query(webpage_url, {'single': True}),
                'duration': parse_duration(self._search_regex(
                    r'<time[^>]+duration[^>]*>([\d:]+)</time>', video, 'duration', fatal=False)),
                'thumbnail': self._search_regex(
                    r'tgme_widget_message_video_thumb"[^>]+background-image:url\(\'([^\']+)\'\)',
                    video, 'thumbnail', fatal=False),
                'formats': formats,
                **message,
            })

        playlist_id = None
        if len(videos) > 1 and 'single' not in parse_qs(url, keep_blank_values=True):
            playlist_id = f'{channel_id}-{msg_id}'

        if self._yes_playlist(playlist_id, msg_id):
            return self.playlist_result(
                videos, playlist_id, format_field(message, 'channel', f'%s {msg_id}'), description)
        else:
            return traverse_obj(videos, lambda _, x: x['id'] == msg_id, get_all=False)
