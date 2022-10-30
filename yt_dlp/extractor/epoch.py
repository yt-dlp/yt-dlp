from .common import InfoExtractor
from ..utils import extract_attributes, get_element_html_by_id


class EpochIE(InfoExtractor):
    _VALID_URL = r'https?://www.theepochtimes\.com/[\w-]+_(?P<id>\d+).html'
    _TESTS = [
        {
            'url': 'https://www.theepochtimes.com/they-can-do-audio-video-physical-surveillance-on-you-24h-365d-a-year-rex-lee-on-intrusive-apps_4661688.html',
            'info_dict': {
                'id': 'a3dd732c-4750-4bc8-8156-69180668bda1',
                'ext': 'mp4',
                'title': '‘They Can Do Audio, Video, Physical Surveillance on You 24H/365D a Year’: Rex Lee on Intrusive Apps',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/the-communist-partys-cyberattacks-on-america-explained-rex-lee-talks-tech-hybrid-warfare_4342413.html',
            'info_dict': {
                'id': '276c7f46-3bbf-475d-9934-b9bbe827cf0a',
                'ext': 'mp4',
                'title': 'The Communist Party’s Cyberattacks on America Explained; Rex Lee Talks Tech Hybrid Warfare',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/kash-patel-a-6-year-saga-of-government-corruption-from-russiagate-to-mar-a-lago_4690250.html',
            'info_dict': {
                'id': 'aa9ceecd-a127-453d-a2de-7153d6fd69b6',
                'ext': 'mp4',
                'title': 'Kash Patel: A ‘6-Year-Saga’ of Government Corruption, From Russiagate to Mar-a-Lago',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/dick-morris-discusses-his-book-the-return-trumps-big-2024-comeback_4819205.html',
            'info_dict': {
                'id': '9489f994-2a20-4812-b233-ac0e5c345632',
                'ext': 'mp4',
                'title': 'Dick Morris Discusses His Book ‘The Return: Trump’s Big 2024 Comeback’',
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        youmaker_video_id = extract_attributes(get_element_html_by_id('videobox', webpage))['data-id']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'http://vs1.youmaker.com/assets/{youmaker_video_id}/playlist.m3u8', video_id, 'mp4', m3u8_id='hls')

        return {
            'id': youmaker_video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': self._html_extract_title(webpage)
        }
