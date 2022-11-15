import re

from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    extract_attributes,
    get_element_html_by_class,
    try_get,
)


class EpochIE(InfoExtractor):
    _VALID_URL = r'https?://www.theepochtimes\.com/[\w-]+_(?P<id>\d+).html'
    _TESTS = [
        {
            'url': 'https://www.theepochtimes.com/they-can-do-audio-video-physical-surveillance-on-you-24h-365d-a-year-rex-lee-on-intrusive-apps_4661688.html',
            'info_dict': {
                'id': 'a3dd732c-4750-4bc8-8156-69180668bda1',
                'ext': 'mp4',
                'title': '‘They Can Do Audio, Video, Physical Surveillance on You 24H/365D a Year’: Rex Lee on Intrusive Apps',
                'description': 'md5:b5f522f96f36997e0957f82910c475c6',
                'thumbnail': r're:https://.*\.jpg',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/the-communist-partys-cyberattacks-on-america-explained-rex-lee-talks-tech-hybrid-warfare_4342413.html',
            'info_dict': {
                'id': '276c7f46-3bbf-475d-9934-b9bbe827cf0a',
                'ext': 'mp4',
                'title': 'The Communist Party’s Cyberattacks on America Explained; Rex Lee Talks Tech Hybrid Warfare',
                'description': 'md5:4c072b26f1f7cfa9a201ac2d482d22b4',
                'thumbnail': r're:https://.*\.jpg',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/kash-patel-a-6-year-saga-of-government-corruption-from-russiagate-to-mar-a-lago_4690250.html',
            'info_dict': {
                'id': 'aa9ceecd-a127-453d-a2de-7153d6fd69b6',
                'ext': 'mp4',
                'title': 'Kash Patel: A ‘6-Year-Saga’ of Government Corruption, From Russiagate to Mar-a-Lago',
                'description': 'md5:f309228a74e15038fc531733449c4318',
                'thumbnail': r're:https://.*\.jpg',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/dick-morris-discusses-his-book-the-return-trumps-big-2024-comeback_4819205.html',
            'info_dict': {
                'id': '9489f994-2a20-4812-b233-ac0e5c345632',
                'ext': 'mp4',
                'title': 'Dick Morris Discusses His Book ‘The Return: Trump’s Big 2024 Comeback’',
                'description': 'md5:bfc57b12437104721ba7b62ae89c5ebe',
                'thumbnail': r're:https://.*\.jpg',
            }
        },
        {
            'note': 'Georestricted to US',
            'url': 'https://www.theepochtimes.com/silence-patton-documentary_4849547.html',
            'info_dict': {
                'id': '4849547',
                'ext': 'mp4',
                'title': 'Silence Patton | Documentary',
                'description': 'Why was General Patton silenced ...',
                'thumbnail': r're:https://.*\.jpg',
            },
            'params': {'skip_download': True},
            'expected_warnings': [
                'This film is only available in the United States because of territorial licensing.'
            ],
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        description = self._og_search_description(webpage, default='NA')
        match = re.match(r'(This film is only available [^.]+\.) *(.*)', description)
        if match:
            self.report_warning(match.group(1), video_id)
            description = match.group(2)

        player = extract_attributes(get_element_html_by_class('player-container', webpage))
        youmaker_video_id = try_get(
            player, lambda x: re.match(r'player-([0-9a-z-]+)$', x['data-id']).group(1))

        if youmaker_video_id:
            video_id = youmaker_video_id
            manifest_url = f'http://vs1.youmaker.com/assets/{youmaker_video_id}/playlist.m3u8'
        elif player.get('data-source', '').endswith('.m3u8'):
            manifest_url = player['data-source']
        else:
            raise UnsupportedError(url)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            manifest_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': self._html_extract_title(webpage),
            'description': description,
            'thumbnail': self._og_search_thumbnail(webpage),
        }
