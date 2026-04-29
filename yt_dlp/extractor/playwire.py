from .common import InfoExtractor
from ..utils import (
    dict_get,
    float_or_none,
)


class PlaywireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:config|cdn)\.playwire\.com(?:/v2)?/(?P<publisher_id>\d+)/(?:videos/v2|embed|config)/(?P<id>\d+)'
    _EMBED_REGEX = [r'<script[^>]+data-config=(["\'])(?P<url>(?:https?:)?//config\.playwire\.com/.+?)\1']

    _TESTS = [{
        'url': 'http://config.playwire.com/14907/videos/v2/3353705/player.json',
        'md5': 'e6398701e3595888125729eaa2329ed9',
        'info_dict': {
            'id': '3353705',
            'ext': 'mp4',
            'title': 'S04_RM_UCL_Rus',
            'thumbnail': r're:^https?://.*\.png$',
            'duration': 145.94,
        },
        'skip': 'Invalid URL',
    }, {
        # m3u8 in f4m
        'url': 'http://config.playwire.com/21772/videos/v2/4840492/zeus.json',
        'info_dict': {
            'id': '4840492',
            'ext': 'mp4',
            'title': 'ITV EL SHOW FULL',
        },
        'skip': 'Invalid URL',
    }, {
        # Multiple resolutions while bitrates missing
        'url': 'http://cdn.playwire.com/11625/embed/85228.html',
        'only_matching': True,
    }, {
        'url': 'http://config.playwire.com/12421/videos/v2/3389892/zeus.json',
        'only_matching': True,
    }, {
        'url': 'http://cdn.playwire.com/v2/12342/config/1532636.json',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.cinemablend.com/new/First-Joe-Dirt-2-Trailer-Teaser-Stupid-Greatness-70874.html',
        'info_dict': {
            'id': '3519514',
            'ext': 'mp4',
            'title': 'Joe Dirt 2 Beautiful Loser Teaser Trailer',
        },
        'skip': 'Site no longer embeds Playwire',
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        publisher_id, video_id = mobj.group('publisher_id'), mobj.group('id')

        player = self._download_json(
            f'http://config.playwire.com/{publisher_id}/videos/v2/{video_id}/zeus.json',
            video_id)

        title = player['settings']['title']
        duration = float_or_none(player.get('duration'), 1000)

        content = player['content']
        thumbnail = content.get('poster')
        src = content['media']['f4m']

        formats = self._extract_f4m_formats(src, video_id, m3u8_id='hls')
        for a_format in formats:
            if not dict_get(a_format, ['tbr', 'width', 'height']):
                a_format['quality'] = 1 if '-hd.' in a_format['url'] else 0

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
        }
