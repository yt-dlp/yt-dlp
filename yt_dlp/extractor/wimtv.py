from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    parse_duration,
    urlencode_postdata,
)


class WimTVIE(InfoExtractor):
    _player = None
    _UUID_RE = r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
    _VALID_URL = r'''(?x:
        https?://platform\.wim\.tv/
        (?:
            (?:embed/)?\?
            |\#/webtv/.+?/
        )
        (?P<type>vod|live|cast)[=/]
        (?P<id>%s).*?)''' % _UUID_RE
    _EMBED_REGEX = [rf'<iframe[^>]+src=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        # vod stream
        'url': 'https://platform.wim.tv/embed/?vod=db29fb32-bade-47b6-a3a6-cb69fe80267a',
        'md5': 'db29fb32-bade-47b6-a3a6-cb69fe80267a',
        'info_dict': {
            'id': 'db29fb32-bade-47b6-a3a6-cb69fe80267a',
            'ext': 'mp4',
            'title': 'AMA SUPERCROSS 2020 - R2 ST. LOUIS',
            'duration': 6481,
            'thumbnail': r're:https?://.+?/thumbnail/.+?/720$'
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # live stream
        'url': 'https://platform.wim.tv/embed/?live=28e22c22-49db-40f3-8c37-8cbb0ff44556&autostart=true',
        'info_dict': {
            'id': '28e22c22-49db-40f3-8c37-8cbb0ff44556',
            'ext': 'mp4',
            'title': 'Streaming MSmotorTV',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://platform.wim.tv/#/webtv/automotornews/vod/422492b6-539e-474d-9c6b-68c9d5893365',
        'only_matching': True,
    }, {
        'url': 'https://platform.wim.tv/#/webtv/renzoarborechannel/cast/f47e0d15-5b45-455e-bf0d-dba8ffa96365',
        'only_matching': True,
    }]

    def _real_initialize(self):
        if not self._player:
            self._get_player_data()

    def _get_player_data(self):
        msg_id = 'Player data'
        self._player = {}

        datas = [{
            'url': 'https://platform.wim.tv/common/libs/player/wimtv/wim-rest.js',
            'vars': [{
                'regex': r'appAuth = "(.+?)"',
                'variable': 'app_auth',
            }]
        }, {
            'url': 'https://platform.wim.tv/common/config/endpointconfig.js',
            'vars': [{
                'regex': r'PRODUCTION_HOSTNAME_THUMB = "(.+?)"',
                'variable': 'thumb_server',
            }, {
                'regex': r'PRODUCTION_HOSTNAME_THUMB\s*\+\s*"(.+?)"',
                'variable': 'thumb_server_path',
            }]
        }]

        for data in datas:
            temp = self._download_webpage(data['url'], msg_id)
            for var in data['vars']:
                val = self._search_regex(var['regex'], temp, msg_id)
                if not val:
                    raise ExtractorError('%s not found' % var['variable'])
                self._player[var['variable']] = val

    def _generate_token(self):
        json = self._download_json(
            'https://platform.wim.tv/wimtv-server/oauth/token', 'Token generation',
            headers={'Authorization': 'Basic %s' % self._player['app_auth']},
            data=urlencode_postdata({'grant_type': 'client_credentials'}))
        token = json.get('access_token')
        if not token:
            raise ExtractorError('access token not generated')
        return token

    def _generate_thumbnail(self, thumb_id, width='720'):
        if not thumb_id or not self._player.get('thumb_server'):
            return None
        if not self._player.get('thumb_server_path'):
            self._player['thumb_server_path'] = ''
        return '%s%s/asset/thumbnail/%s/%s' % (
            self._player['thumb_server'],
            self._player['thumb_server_path'],
            thumb_id, width)

    def _real_extract(self, url):
        urlc = self._match_valid_url(url).groupdict()
        video_id = urlc['id']
        stream_type = is_live = None
        if urlc['type'] in {'live', 'cast'}:
            stream_type = urlc['type'] + '/channel'
            is_live = True
        else:
            stream_type = 'vod'
            is_live = False
        token = self._generate_token()
        json = self._download_json(
            'https://platform.wim.tv/wimtv-server/api/public/%s/%s/play' % (
                stream_type, video_id), video_id,
            headers={'Authorization': 'Bearer %s' % token,
                     'Content-Type': 'application/json'},
            data=bytes('{}', 'utf-8'))

        formats = []
        for src in json.get('srcs') or []:
            if src.get('mimeType') == 'application/x-mpegurl':
                formats.extend(
                    self._extract_m3u8_formats(
                        src.get('uniqueStreamer'), video_id, 'mp4'))
            if src.get('mimeType') == 'video/flash':
                formats.append({
                    'format_id': 'rtmp',
                    'url': src.get('uniqueStreamer'),
                    'ext': determine_ext(src.get('uniqueStreamer'), 'flv'),
                    'rtmp_live': is_live,
                })
        json = json.get('resource')
        thumb = self._generate_thumbnail(json.get('thumbnailId'))

        return {
            'id': video_id,
            'title': json.get('title') or json.get('name'),
            'duration': parse_duration(json.get('duration')),
            'formats': formats,
            'thumbnail': thumb,
            'is_live': is_live,
        }
