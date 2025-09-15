from .common import InfoExtractor
from ..utils import remove_end


class CharlieRoseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?charlierose\.com/(?:video|episode)(?:s|/player)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://charlierose.com/videos/27996',
        'md5': '4405b662f557f94aa256fa6a7baf7426',
        'info_dict': {
            'id': '27996',
            'ext': 'mp4',
            'title': 'Remembering Zaha Hadid',
            'thumbnail': r're:^https?://.*\.jpg\?\d+',
            'description': 'We revisit past conversations with Zaha Hadid, in memory of the world renowned Iraqi architect.',
            'subtitles': {
                'en': [{
                    'ext': 'vtt',
                }],
            },
        },
    }, {
        'url': 'https://charlierose.com/videos/27996',
        'only_matching': True,
    }, {
        'url': 'https://charlierose.com/episodes/30887?autoplay=true',
        'only_matching': True,
    }]

    _PLAYER_BASE = 'https://charlierose.com/video/player/%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(self._PLAYER_BASE % video_id, video_id)

        title = remove_end(self._og_search_title(webpage), ' - Charlie Rose')

        info_dict = self._parse_html5_media_entries(
            self._PLAYER_BASE % video_id, webpage, video_id,
            m3u8_entry_protocol='m3u8_native')[0]
        self._remove_duplicate_formats(info_dict['formats'])
        for fmt in info_dict['formats']:
            if fmt.get('protocol') == 'm3u8_native':
                fmt['__needs_testing'] = True

        info_dict.update({
            'id': video_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            '_format_sort_fields': ('proto',),
        })

        return info_dict
