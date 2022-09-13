from .common import InfoExtractor
from ..utils import int_or_none, merge_dicts, try_call


class DetikEmbedIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        # cnn embed
        'url': 'https://www.cnnindonesia.com/embed/video/846189',
        'info_dict': {
            'id': '846189',
            'ext': 'mp4',
            'description': 'md5:ece7b003b3ee7d81c6a5cfede7d5397d',
            'thumbnail': r're:https?://akcdn\.detik\.net\.id/visual/2022/09/11/thumbnail-video-1_169.jpeg',
            'title': 'Video CNN Indonesia - VIDEO: Momen Charles Disambut Meriah usai Dilantik jadi Raja Inggris',
            'age_limit': 0,
            'tags': ['raja charles', ' raja charles iii', ' ratu elizabeth', ' ratu elizabeth meninggal dunia', ' raja inggris', ' inggris'],
            'subtitle': {},
            'release_timestamp': 1662869995,
            'release_date': '20220911',
        }
    }, {
        # 20.detik
        'url': 'https://20.detik.com/otobuzz/20220704-220704093/mulai-rp-10-jutaan-ini-skema-kredit-mitsubishi-pajero-sport',
        'info_dict': {
            'id': '220704093',
            'ext': 'mp4',
            'description': 'md5:9b2257341b6f375cdcf90106146d5ffb',
            'thumbnail': r're:https?://cdnv\.detik\.com/videoservice/AdminTV/2022/07/04/5d6187e402ec4a91877755a5886ff5b6-20220704161859-0s.jpg',
            'title': 'Mulai Rp 10 Jutaan! Ini Skema Kredit Mitsubishi Pajero Sport',
            'timestamp': 1656951521,
            'upload_date': '20220704',
            'duration': 83.0,
            'tags': ['cicilan mobil', 'mitsubishi pajero sport', 'mitsubishi', 'pajero sport'],
            'release_timestamp': 1656926321,
            'release_date': '20220704',
            'age_limit': 0,
            'subtitle': {},
        }
    }, {
        # pasangmata.detik
        'url': 'https://pasangmata.detik.com/contribution/366649',
        'info_dict': {
            'id': '366649',
            'ext': 'mp4',
            'title': 'Saling Dorong Aparat dan Pendemo di Aksi Tolak Kenaikan BBM',
            'description': 'md5:7a6580876c8381c454679e028620bea7',
            'age_limit': 0,
            'tags': 'count:17',
            'subtitle': {},
        }
    }]

    def _extract_from_webpage(self, url, webpage):
        video_id = (self._search_regex(r'identifier\s*:\s*\'([^\']+)', webpage, 'identifier', default=False, fatal=False)
                    or self._html_search_meta(['video_id', 'dtk:video_id'], webpage, fatal=False))
        player_type, video_data = self._search_regex(
            r'<script\s*[^>]+src="https?://(aws)?cdn\.detik\.net\.id/(?P<type>flowplayer|detikVideo)[^>]+>\s*(?P<video_data>{[^}]+})',
            webpage, 'playerjs', group=('type', 'video_data'), default=(None, ''))

        json_ld_data = self._search_json_ld(webpage, video_id, default={})
        thumbnail_url = None
        if not player_type:
            return
        elif player_type == 'flowplayer':
            video_json_data = self._parse_json(video_data.replace('\'', '"'), None)
            video_url = video_json_data['videoUrl']
            thumbnail_url = video_json_data.get('imageUrl')

        elif player_type == 'detikVideo':
            video_url = self._search_regex(
                r'videoUrl\s*:\s*[\'"]?([^"\']+)', video_data, 'videoUrl')
            thumbnail_url = self._search_regex(
                r'imageUrl\s*:\s*[\'"]?([^"\']+)', video_data, 'videoUrl')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id)
        self._sort_formats(formats)

        yield merge_dicts(json_ld_data, {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'originalTitle'], webpage),
            'thumbnail': thumbnail_url or self._html_search_meta(['og:image', 'twitter:image:src', 'thumbnailUrl', 'dtk:thumbnailUrl'], webpage),
            'description': self._html_search_meta(['og:description', 'twitter:description', 'description'], webpage),
            'formats': formats,
            'subtitle': subtitles,
            'tags': try_call(lambda: self._html_search_meta(
                ['keywords', 'keyword', 'dtk:keywords'], webpage).split(',')),
            # 'duration': int_or_none(self._html_search_meta('duration', webpage, fatal=False)),
            'release_timestamp': int_or_none(self._html_search_meta('dtk:publishdateunix', webpage, fatal=False), 1000),
        })
