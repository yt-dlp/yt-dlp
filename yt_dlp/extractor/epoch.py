from .common import InfoExtractor


class EpochIE(InfoExtractor):
    _VALID_URL = r'https?://www.theepochtimes\.com/[\w-]+_(?P<id>\d+).html'
    _YOUMAKER_MANIFEST_URL = 'http://vs1.youmaker.com/assets/{0}/playlist.m3u8'
    _TESTS = [
        {
            'url': 'https://www.theepochtimes.com/they-can-do-audio-video-physical-surveillance-on-you-24h-365d-a-year-rex-lee-on-intrusive-apps_4661688.html',
            'info_dict': {
                'id': '4661688',
                'ext': 'mp4',
                'title': '‘They Can Do Audio, Video, Physical Surveillance on You 24H/365D a Year’: Rex Lee on Intrusive Apps',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/the-communist-partys-cyberattacks-on-america-explained-rex-lee-talks-tech-hybrid-warfare_4342413.html',
            'info_dict': {
                'id': '4342413',
                'ext': 'mp4',
                'title': 'The Communist Party’s Cyberattacks on America Explained; Rex Lee Talks Tech Hybrid Warfare',
            }
        },
        {
            'url': 'https://www.theepochtimes.com/kash-patel-a-6-year-saga-of-government-corruption-from-russiagate-to-mar-a-lago_4690250.html',
            'info_dict': {
                'id': '4690250',
                'ext': 'mp4',
                'title': 'Kash Patel: A ‘6-Year-Saga’ of Government Corruption, From Russiagate to Mar-a-Lago',
            }
        },
    ]

    def _real_extract(self, url):

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_extract_title(webpage)
        youmaker_video_id = self._search_regex(
            r'data-trailer="[\w-]+" data-id="([\w-]+)"', webpage, 'url')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._YOUMAKER_MANIFEST_URL.format(youmaker_video_id), video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': title
        }
