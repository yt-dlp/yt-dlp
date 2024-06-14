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
        'url': 'https://player.stv.tv/video/4gwd/emmerdale/60-seconds-on-set-with-laura-norton/',
        'md5': '5adf9439c31d554f8be0707c7abe7e0a',
        'info_dict': {
            'id': '5333973339001',
            'ext': 'mp4',
            'upload_date': '20170301',
            'title': '60 seconds on set with Laura Norton',
            'description': "How many questions can Laura - a.k.a Kerry Wyatt - answer in 60 seconds? Let's find out!",
            'timestamp': 1488388054,
            'uploader_id': '1486976045',
        },
        'skip': 'this resource is unavailable outside of the UK',
    }, {
        # episodes
        'url': 'https://player.stv.tv/episode/4125/jennifer-saunders-memory-lane',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1486976045/default_default/index.html?videoId=%s'
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
        if programme.get('drmEnabled'):
            self.report_drm(video_id)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {'geo_countries': ['GB']}),
            'description': result.get('summary'),
            'duration': float_or_none(video.get('length'), 1000),
            'subtitles': subtitles,
            'view_count': int_or_none(result.get('views')),
            'series': programme.get('name') or programme.get('shortName'),
            'ie_key': 'BrightcoveNew',
        }
