from urllib.parse import unquote

from .common import InfoExtractor
from ..utils import (
    merge_dicts,
    urljoin,
)


class WakanimIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?wakanim\.tv/[^/]+/v2/catalogue/episode/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.wakanim.tv/de/v2/catalogue/episode/2997/the-asterisk-war-omu-staffel-1-episode-02-omu',
        'info_dict': {
            'id': '2997',
            'ext': 'mp4',
            'title': 'Episode 02',
            'description': 'md5:2927701ea2f7e901de8bfa8d39b2852d',
            'series': 'The Asterisk War  (OmU.)',
            'season_number': 1,
            'episode': 'Episode 02',
            'episode_number': 2,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # DRM Protected
        'url': 'https://www.wakanim.tv/de/v2/catalogue/episode/7843/sword-art-online-alicization-omu-arc-2-folge-15-omu',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        if 'Geoblocking' in webpage:
            if '/de/' in url:
                self.raise_geo_restricted(countries=['DE', 'AT', 'CH'])
            else:
                self.raise_geo_restricted(countries=['RU'])

        manifest_url = urljoin(url, self._search_regex(
            r'file\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage, 'manifest url',
            group='url'))
        if not self.get_param('allow_unplayable_formats'):
            # https://docs.microsoft.com/en-us/azure/media-services/previous/media-services-content-protection-overview#streaming-urls
            encryption = self._search_regex(
                r'encryption%3D(c(?:enc|bc(?:s-aapl)?))',
                manifest_url, 'encryption', default=None)
            if encryption in ('cenc', 'cbcs-aapl'):
                self.report_drm(video_id)

        if 'format=mpd-time-cmaf' in unquote(manifest_url):
            formats = self._extract_mpd_formats(
                manifest_url, video_id, mpd_id='dash')
        else:
            formats = self._extract_m3u8_formats(
                manifest_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls')

        info = self._search_json_ld(webpage, video_id, default={})

        title = self._search_regex(
            (r'<h1[^>]+\bclass=["\']episode_h1[^>]+\btitle=(["\'])(?P<title>(?:(?!\1).)+)\1',
             r'<span[^>]+\bclass=["\']episode_title["\'][^>]*>(?P<title>[^<]+)'),
            webpage, 'title', default=None, group='title')

        return merge_dicts(info, {
            'id': video_id,
            'title': title,
            'formats': formats,
        })
