from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    smuggle_url,
    str_or_none,
    try_get,
)


class STVPlayerIE(InfoExtractor):
    IE_NAME = 'stv:player'
    _VALID_URL = r'https?://player\.stv\.tv/(?P<type>episode|video)/(?P<id>[a-z0-9]{4})'
    _TESTS = [{
        # shortform
        'url': 'https://player.stv.tv/video/8r2v/archie/interview-with-jason-isaacs-and-laura-aikman',
        'md5': 'ef6e9fb1c3d660b68f7ca86dc9dcf592',
        'info_dict': {
            'id': '6341315073112',
            'ext': 'mp4',
            'upload_date': '20231117',
            'title': 'Archie - Extras - Interview with Jason Isaacs and Laura Aikman',
            'description': 'md5:fe62251499216500d4953c632c5c71cc',
            'timestamp': 1700240365,
            'uploader_id': '1486976045',
            'tags': ['vp-archie-sf'],
            'series': 'Archie',
            'duration': 310.144,
            'thumbnail': r're:https://.*/image\.jpg',
        },
    }, {
        # episodes
        'url': 'https://player.stv.tv/episode/3sjc/seans-scotland',
        'md5': '445f45f4cbba97886dcfd5e51f76a537',
        'info_dict': {
            'id': '6043990119001',
            'ext': 'mp4',
            'upload_date': '20190603',
            'title': 'Sean\'s Scotland - Monday, June 3, 2019',
            'description': 'md5:4c824ea1edd70afc5088f1616ca598f2',
            'timestamp': 1559559623,
            'uploader_id': '1486976045',
            'tags': ['vp-seans-scotland'],
            'series': 'Sean\'s Scotland',
            'view_count': int,
            'duration': 1340.075,
            'thumbnail': r're:https://.*/image\.jpg',
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _PTYPE_MAP = {
        'episode': 'episodes',
        'video': 'shortform',
    }

    def _real_extract(self, url):
        ptype, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, video_id, fatal=False) or ''
        props = self._search_nextjs_data(webpage, video_id, default={}).get('props') or {}
        player_api_cache = try_get(
            props, lambda x: x['initialReduxState']['playerApiCache']) or {}

        api_path, resp = None, {}
        for k, v in player_api_cache.items():
            if k.startswith(('/episodes/', '/shortform/')):
                api_path, resp = k, v
                break
        else:
            episode_id = str_or_none(try_get(
                props, lambda x: x['pageProps']['episodeId']))
            api_path = f'/{self._PTYPE_MAP[ptype]}/{episode_id or video_id}'

        result = resp.get('results')
        if not result:
            resp = self._download_json(
                'https://player.api.stv.tv/v1' + api_path, video_id)
            result = resp['results']

        video = result['video']
        video_id = str(video['id'])

        subtitles = {}
        _subtitles = result.get('_subtitles') or {}
        for ext, sub_url in _subtitles.items():
            subtitles.setdefault('en', []).append({
                'ext': 'vtt' if ext == 'webvtt' else ext,
                'url': sub_url,
            })

        programme = result.get('programme') or {}
        account_id = '1486976045'
        if programme.get('drmEnabled'):
            if not self.get_param('allow_unplayable_formats'):
                self.report_drm(video_id)
            else:
                account_id = '6204867266001'

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % (account_id, video_id),
                {'geo_countries': ['GB']}),
            'description': result.get('summary'),
            'duration': float_or_none(video.get('length'), 1000),
            'subtitles': subtitles,
            'view_count': int_or_none(result.get('views')),
            'series': programme.get('name') or programme.get('shortName'),
            'ie_key': 'BrightcoveNew',
        }
