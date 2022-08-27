from .common import InfoExtractor
from ..utils import (
    unescapeHTML
)


class EpochIE(InfoExtractor):
    _VALID_URL = r'https?://www.theepochtimes\.com/[\w-]+_(?P<id>\d+).html'
    _TESTS = [
        {
            'url': 'https://www.theepochtimes.com/they-can-do-audio-video-physical-surveillance-on-you-24h-365d-a-year-rex-lee-on-intrusive-apps_4661688.html',
            'info_dict': {
                "id": '4661688',
                'ext': 'mp4',
                'url': 'http://vs1.youmaker.com/assets/a3dd732c-4750-4bc8-8156-69180668bda1/playlist.m3u8',
                'title': '‘They Can Do Audio, Video, Physical Surveillance on You 24H/365D a Year’: Rex Lee on Intrusive Apps',
                'webpage_url_domain': 'theepochtimes.com',
                'extractor': 'Epoch',
                'extractor_key': 'Epoch'
            }
        },
        {
            'url': 'https://www.theepochtimes.com/the-communist-partys-cyberattacks-on-america-explained-rex-lee-talks-tech-hybrid-warfare_4342413.html',
            'info_dict': {
                'id': '4342413',
                'ext': 'mp4',
                'url': 'https://vs1.youmaker.com/assets/276c7f46-3bbf-475d-9934-b9bbe827cf0a/playlist.m3u8',
                'title': 'The Communist Party’s Cyberattacks on America Explained; Rex Lee Talks Tech Hybrid Warfare',
                'webpage_url_domain': 'theepochtimes.com',
                'extractor': 'Epoch',
                'extractor_key': 'Epoch'
            }
        },
    ]

    def _real_extract(self, url):

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._search_regex('<title>(?P<title>.*)<\/title>', unescapeHTML(webpage), 'title', group='title')
        youmaker_video_id = self._search_regex('<div class="videobox" id="videobox" data-trailer="[\w-]+" data-id="([\w-]+)">', webpage, 'url')

        return {
            "id": video_id,
            "ext": "mp4",
            "url": f"http://vs1.youmaker.com/assets/{youmaker_video_id}/playlist.m3u8",
            "title": title
        }
