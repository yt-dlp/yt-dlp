from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class SwisscomWebcastIE(InfoExtractor):
    _VALID_URL = r'https?://webcast\.swisscom\.ch/csr/#/webcast/(?P<id>[0-9a-f]+)/(?P<lang>\w+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\b(data-)?src=[\'"](?P<url>{_VALID_URL})']
    _WEBPAGE_TESTS = [{
        'url': 'https://www.snb.ch/en/services-events/digital-services/research-tv/researchtv-2025-10-02',
        'info_dict': {
            'id': '68bff74a1a4700fbff5f2f52',
            'ext': 'mp4',
            'title': 'Karl Brunner Distinguished Lecture 2025 by John H. Cochrane (Hoover Institution)',
            'alt_title': '02.10.2025 - SNB Karl Brunner 2025_Edit',
            'description': '',
            'uploader_id': '595641605a53b88591267f02',
            'uploader': 'SNB Research',
            'release_timestamp': 1759419000,
            'modified_timestamp': 1759485387,
            'release_date': '20251002',
            'modified_date': '20251003',
        },
    }, {
        'url': 'https://www.snb.ch/de/services-events/digital-services/webtv/webtv-2025-12-11',
        'info_dict': {
            'id': '6931515f908625503c38a9b2',
            'ext': 'mp4',
            'title': 'Mediengespräch der Schweizerischen Nationalbank vom 11. Dezember 2025',
            'alt_title': 'Mediengespräch der Schweizerischen Nationalbank vom 11. Dezember 2025',
            'description': 'Bern, Beginn 10.00 Uhr (Schweizer Zeit)',
            'uploader_id': '5fb28a2c41e5990e2d58908d',
            'uploader': 'SNB Public',
            'release_timestamp': 1765443600,
            'modified_timestamp': 1765449001,
            'release_date': '20251211',
            'modified_date': '20251211',
        },
    }]

    def _real_extract(self, url):
        video_id, lang = self._match_valid_url(url).group('id', 'lang')

        token = self._download_json(f'https://webcast.swisscom.ch/api/v1/login/webcast/{video_id}', video_id, 'Downloading access token')['token']

        data = self._download_json(f'https://webcast.swisscom.ch/api/v1/public/webcast/{video_id}', video_id, headers={'Authorization': f'Bearer {token}'})
        info = next(l for l in data['languages'] if l['language'] == lang)

        formats = self._extract_m3u8_formats(info['player']['hlsUrl'], video_id)

        return {
            'id': video_id,
            **traverse_obj(info, {
                'title': 'name',
                'alt_title': ('player', 'videoTitle'),
                'description': 'description',
            }),
            **traverse_obj(data, {
                'uploader_id': ('customer', 'id'),
                'uploader': ('customer', 'name'),
                'release_timestamp': ('startDate', {int_or_none(scale=1000)}),
                'modified_timestamp': ('lastUpdated', {int}),
            }),
            'formats': formats,
        }
