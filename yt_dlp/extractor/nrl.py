
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    get_element_by_class,
    traverse_obj,
    unified_timestamp,
)


class NRLTVIE(InfoExtractor):
    IE_NAME = 'nrlwatch'
    IE_DESC = 'NRL.com Watch'
    _VALID_URL = r'https?://(?:www\.)?nrl\.com/watch(?:/[^/?#]+)*/(?P<id>[^/?#]+)'
    _GEO_COUNTRIES = ['AU']
    _TESTS = [{
        # Globally available video
        'url': 'https://www.nrl.com/watch/news/match-highlights-titans-v-knights-862805/',
        'info_dict': {
            'id': 'match-highlights-titans-v-knights-862805',
            'ext': 'mp4',
            'title': 'Match Highlights: Titans v Knights',
            'description': 'The Gold Coast host Newcastle in round 6 of the 2019 NRL Telstra Premiership',
            'duration': 270.0,
            'thumbnail': 'https://www.nrl.com/remote.axd?https://imageproxy-prod.nrl.digital/api/assets/28839369/keyframes/273128/image?center=0.427%2C0.513&preset=seo-card-large',
            'season': '2019',
            'season_id': '2019',
            'timestamp': 1555894764,
            'upload_date': '20190422',
            'modified_timestamp': 1724762491,
            'modified_date': '20240827',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # Geo-restricted video (bypassable via X-Forwarded-For)
        # Also: Video with broken 1080p format
        'url': 'https://www.nrl.com/watch/matches/telstra-premiership/2025/grand-final/full-match-replay-storm-v-broncos---grand-final-2025/',
        'info_dict': {
            'id': 'full-match-replay-storm-v-broncos---grand-final-2025',
            'ext': 'mp4',
            'title': 'Full Match Replay: Storm v Broncos - Grand Final 2025',
            'description': 'The Melbourne Storm and Brisbane Broncos face off in the 2025 NRL Telstra Premiership Grand Final',
            'duration': 6666.0,
            'thumbnail': 'https://www.nrl.com/remote.axd?https://imageproxy-prod.nrl.digital/api/assets/79824761/keyframes/554177/image?center=0.5%2C0.5&preset=seo-card-large',
            'season': '2025',
            'season_id': '2025',
            'timestamp': 1759707882,
            'upload_date': '20251005',
            'modified_timestamp': 1759919888,
            'modified_date': '20251008',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # Video requiring login
        'url': 'https://www.nrl.com/watch/matches/telstra-premiership/2019/round-6/full-match-replay-titans-v-knights---round-6-2019/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if get_element_by_class('locked-content-video-wrapper', webpage):
            self.raise_login_required(method='cookies')

        q_data = self._parse_json(self._html_search_regex(
            r'(?s)q-data="({.+?})"', webpage, 'player data'), video_id)

        formats = self._extract_m3u8_formats(q_data['streams']['hls'], video_id, 'mp4')
        # The 1080p formats for full matches are just broken (failing to play in a browser as well).
        # We don't have a reliable condition to detect these up front,
        # so mark all formats as __needs_testing to be safe.
        for fmt in formats:
            fmt['__needs_testing'] = True

        return {
            **self._search_json_ld(webpage, video_id, fatal=False),
            **traverse_obj(q_data, {
                'title': ('name', {str}),
                'description': ('summary', {str}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('published', {unified_timestamp}),
                'modified_timestamp': ('lastModified', {unified_timestamp}),
                'season_id': ('tags', 'season', 'id', {str}),
                'season': ('tags', 'season', 'name', {str}),
            }),
            'formats': formats,
            'id': video_id,
        }
