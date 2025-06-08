import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_id,
)


class MaveIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<channel_id>[a-z]+)\.mave\.digital/ep-(?P<short_id>[0-9]+)'
    _TESTS = [
        {
            'url': 'https://ochenlichnoe.mave.digital/ep-25',
            'md5': 'aa3e513ef588b4366df1520657cbc10c',
            'info_dict': {
                'id': 'ochenlichnoe-25',
                'title': 'Между мной и миром: психология самооценки',
                'description': 'md5:83183d7002dc32fbebc3ccecd4a1ac03',
                'thumbnail': r're:https?://.*\.jpg$',
                'ext': 'mp3',
                'channel': 'Очень личное',
                'channel_id': 'ochenlichnoe',
                'channel_url': 'https://ochenlichnoe.mave.digital/',
            },
        },
        {
            'url': 'https://budem.mave.digital/ep-12',
            'md5': 'e1ce2780fcdb6f17821aa3ca3e8c919f',
            'info_dict': {
                'id': 'budem-12',
                'title': 'Екатерина Михайлова: "Горе от ума" не про женщин написана',
                'description': 'md5:d9ce1fc1fb5fc7b7a4e7a0b84a7861c3',
                'thumbnail': r're:https?://.*\.jpg$',
                'ext': 'mp3',
                'channel': 'Все там будем',
                'channel_id': 'budem',
                'channel_url': 'https://budem.mave.digital/',
            },
        },
    ]

    def _real_extract(self, url):
        channel_id, short_id = self._match_valid_url(url).group('channel_id', 'short_id')

        channel_url = f'https://{channel_id}.mave.digital/'

        video_id = f'{channel_id}-{short_id}'

        webpage = self._download_webpage(url, video_id)

        # Format: "TITLE — Подкаст «CHANNEL»"
        page_title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        match = re.search(r'^(.+?)\s*—\s*(.+?)«(.+?)»', page_title)
        title = match.group(1).strip()
        channel = match.group(3).strip()

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'channel': channel,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'url': self._mave_link(webpage, video_id),
            'thumbnail': self._og_search_thumbnail(webpage),
        }

    def _mave_link(self, webpage, video_id):
        data = get_element_by_id('__NUXT_DATA__', webpage)

        jdata = json.loads(data)

        for value in jdata:
            if isinstance(value, str):
                if value.endswith('.mp3'):
                    link_id = value
                    break

        if link_id is None:
            raise ExtractorError('Unable to find mp3 file link', video_id=video_id)

        return 'https://api.mave.digital/' + link_id
