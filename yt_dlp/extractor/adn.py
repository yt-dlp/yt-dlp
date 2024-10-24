import base64
import binascii
import json
import os
import random
import time

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    ass_subtitles_timecode,
    bytes_to_intlist,
    bytes_to_long,
    float_or_none,
    int_or_none,
    intlist_to_bytes,
    join_nonempty,
    long_to_bytes,
    parse_iso8601,
    pkcs1pad,
    str_or_none,
    strip_or_none,
    try_get,
    unified_strdate,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class ADNBaseIE(InfoExtractor):
    IE_DESC = 'Animation Digital Network'
    _NETRC_MACHINE = 'animationdigitalnetwork'
    _BASE = 'animationdigitalnetwork.fr'
    _API_BASE_URL = f'https://gw.api.{_BASE}/'
    _PLAYER_BASE_URL = f'{_API_BASE_URL}player/'
    _HEADERS = {}
    _LOGIN_ERR_MESSAGE = 'Unable to log in'
    _RSA_KEY = (0x9B42B08905199A5CCE2026274399CA560ECB209EE9878A708B1C0812E1BB8CB5D1FB7441861147C1A1F2F3A0476DD63A9CAC20D3E983613346850AA6CB38F16DC7D720FD7D86FC6E5B3D5BBC72E14CD0BF9E869F2CEA2CCAD648F1DCE38F1FF916CEFB2D339B64AA0264372344BC775E265E8A852F88144AB0BD9AA06C1A4ABB, 65537)
    _POS_ALIGN_MAP = {
        'start': 1,
        'end': 3,
    }
    _LINE_ALIGN_MAP = {
        'middle': 8,
        'end': 4,
    }


class ADNIE(ADNBaseIE):
    _VALID_URL = r'https?://(?:www\.)?animationdigitalnetwork\.com/(?:(?P<lang>de)/)?video/[^/?#]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://animationdigitalnetwork.com/video/558-fruits-basket/9841-episode-1-a-ce-soir',
        'md5': '1c9ef066ceb302c86f80c2b371615261',
        'info_dict': {
            'id': '9841',
            'ext': 'mp4',
            'title': 'Fruits Basket - Episode 1',
            'description': 'md5:14be2f72c3c96809b0ca424b0097d336',
            'series': 'Fruits Basket',
            'duration': 1437,
            'release_date': '20190405',
            'comment_count': int,
            'average_rating': float,
            'season_number': 1,
            'episode': 'À ce soir !',
            'episode_number': 1,
            'thumbnail': str,
            'season': 'Season 1',
        },
        'skip': 'Only available in French and German speaking Europe',
    }, {
        'url': 'https://animationdigitalnetwork.com/de/video/973-the-eminence-in-shadow/23550-folge-1',
        'md5': '5c5651bf5791fa6fcd7906012b9d94e8',
        'info_dict': {
            'id': '23550',
            'ext': 'mp4',
            'episode_number': 1,
            'duration': 1417,
            'release_date': '20231004',
            'series': 'The Eminence in Shadow',
            'season_number': 2,
            'episode': str,
            'title': str,
            'thumbnail': str,
            'season': 'Season 2',
            'comment_count': int,
            'average_rating': float,
            'description': str,
        },
        # 'skip': 'Only available in French and German speaking Europe',
    }]

    def _get_subtitles(self, sub_url, video_id):
        if not sub_url:
            return None

        enc_subtitles = self._download_webpage(
            sub_url, video_id, 'Downloading subtitles location', fatal=False) or '{}'
        subtitle_location = (self._parse_json(enc_subtitles, video_id, fatal=False) or {}).get('location')
        if subtitle_location:
            enc_subtitles = self._download_webpage(
                subtitle_location, video_id, 'Downloading subtitles data',
                fatal=False, headers={'Origin': 'https://' + self._BASE})
        if not enc_subtitles:
            return None

        # http://animationdigitalnetwork.fr/components/com_vodvideo/videojs/adn-vjs.min.js
        dec_subtitles = unpad_pkcs7(aes_cbc_decrypt_bytes(
            base64.b64decode(enc_subtitles[24:]),
            binascii.unhexlify(self._K + '7fac1178830cfe0c'),
            base64.b64decode(enc_subtitles[:24])))
        subtitles_json = self._parse_json(dec_subtitles.decode(), None, fatal=False)
        if not subtitles_json:
            return None

        subtitles = {}
        for sub_lang, sub in subtitles_json.items():
            ssa = '''[Script Info]
ScriptType:V4.00
[V4 Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,TertiaryColour,BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,AlphaLevel,Encoding
Style: Default,Arial,18,16777215,16777215,16777215,0,-1,0,1,1,0,2,20,20,20,0,0
[Events]
Format: Marked,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text'''
            for current in sub:
                start, end, text, line_align, position_align = (
                    float_or_none(current.get('startTime')),
                    float_or_none(current.get('endTime')),
                    current.get('text'), current.get('lineAlign'),
                    current.get('positionAlign'))
                if start is None or end is None or text is None:
                    continue
                alignment = self._POS_ALIGN_MAP.get(position_align, 2) + self._LINE_ALIGN_MAP.get(line_align, 0)
                ssa += os.linesep + 'Dialogue: Marked=0,{},{},Default,,0,0,0,,{}{}'.format(
                    ass_subtitles_timecode(start),
                    ass_subtitles_timecode(end),
                    '{\\a%d}' % alignment if alignment != 2 else '',
                    text.replace('\n', '\\N').replace('<i>', '{\\i1}').replace('</i>', '{\\i0}'))

            if sub_lang == 'vostf':
                sub_lang = 'fr'
            elif sub_lang == 'vostde':
                sub_lang = 'de'
            subtitles.setdefault(sub_lang, []).extend([{
                'ext': 'json',
                'data': json.dumps(sub),
            }, {
                'ext': 'ssa',
                'data': ssa,
            }])
        return subtitles

    def _perform_login(self, username, password):
        try:
            access_token = (self._download_json(
                self._API_BASE_URL + 'authentication/login', None,
                'Logging in', self._LOGIN_ERR_MESSAGE, fatal=False,
                data=urlencode_postdata({
                    'password': password,
                    'rememberMe': False,
                    'source': 'Web',
                    'username': username,
                })) or {}).get('accessToken')
            if access_token:
                self._HEADERS['Authorization'] = f'Bearer {access_token}'
        except ExtractorError as e:
            message = None
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                resp = self._parse_json(
                    e.cause.response.read().decode(), None, fatal=False) or {}
                message = resp.get('message') or resp.get('code')
            self.report_warning(message or self._LOGIN_ERR_MESSAGE)

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        self._HEADERS['X-Target-Distribution'] = lang or 'fr'
        video_base_url = self._PLAYER_BASE_URL + f'video/{video_id}/'
        player = self._download_json(
            video_base_url + 'configuration', video_id,
            'Downloading player config JSON metadata',
            headers=self._HEADERS)['player']
        options = player['options']

        user = options['user']
        if not user.get('hasAccess'):
            start_date = traverse_obj(options, ('video', 'startDate', {str}))
            if (parse_iso8601(start_date) or 0) > time.time():
                raise ExtractorError(f'This video is not available yet. Release date: {start_date}', expected=True)
            self.raise_login_required('This video requires a subscription', method='password')

        token = self._download_json(
            user.get('refreshTokenUrl') or (self._PLAYER_BASE_URL + 'refresh/token'),
            video_id, 'Downloading access token', headers={
                'X-Player-Refresh-Token': user['refreshToken'],
            }, data=b'')['token']

        links_url = try_get(options, lambda x: x['video']['url']) or (video_base_url + 'link')
        self._K = ''.join(random.choices('0123456789abcdef', k=16))
        message = bytes_to_intlist(json.dumps({
            'k': self._K,
            't': token,
        }))

        # Sometimes authentication fails for no good reason, retry with
        # a different random padding
        links_data = None
        for _ in range(3):
            padded_message = intlist_to_bytes(pkcs1pad(message, 128))
            n, e = self._RSA_KEY
            encrypted_message = long_to_bytes(pow(bytes_to_long(padded_message), e, n))
            authorization = base64.b64encode(encrypted_message).decode()

            try:
                links_data = self._download_json(
                    links_url, video_id, 'Downloading links JSON metadata', headers={
                        'X-Player-Token': authorization,
                        **self._HEADERS,
                    }, query={
                        'freeWithAds': 'true',
                        'adaptive': 'false',
                        'withMetadata': 'true',
                        'source': 'Web',
                    })
                break
            except ExtractorError as e:
                if not isinstance(e.cause, HTTPError):
                    raise e

                if e.cause.status == 401:
                    # This usually goes away with a different random pkcs1pad, so retry
                    continue

                error = self._parse_json(e.cause.response.read(), video_id)
                message = error.get('message')
                if e.cause.code == 403 and error.get('code') == 'player-bad-geolocation-country':
                    self.raise_geo_restricted(msg=message)
                raise ExtractorError(message)
        else:
            raise ExtractorError('Giving up retrying')

        links = links_data.get('links') or {}
        metas = links_data.get('metadata') or {}
        sub_url = (links.get('subtitles') or {}).get('all')
        video_info = links_data.get('video') or {}
        title = metas['title']

        formats = []
        for format_id, qualities in (links.get('streaming') or {}).items():
            if not isinstance(qualities, dict):
                continue
            for quality, load_balancer_url in qualities.items():
                load_balancer_data = self._download_json(
                    load_balancer_url, video_id,
                    f'Downloading {format_id} {quality} JSON metadata',
                    headers=self._HEADERS,
                    fatal=False) or {}
                m3u8_url = load_balancer_data.get('location')
                if not m3u8_url:
                    continue
                m3u8_formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id, fatal=False)
                if format_id == 'vf':
                    for f in m3u8_formats:
                        f['language'] = 'fr'
                elif format_id == 'vde':
                    for f in m3u8_formats:
                        f['language'] = 'de'
                formats.extend(m3u8_formats)

        if not formats:
            self.raise_login_required('This video requires a subscription', method='password')

        video = (self._download_json(
            self._API_BASE_URL + f'video/{video_id}', video_id,
            'Downloading additional video metadata', fatal=False, headers=self._HEADERS) or {}).get('video') or {}
        show = video.get('show') or {}

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(metas.get('summary') or video.get('summary')),
            'thumbnail': video_info.get('image') or player.get('image'),
            'formats': formats,
            'subtitles': self.extract_subtitles(sub_url, video_id),
            'episode': metas.get('subtitle') or video.get('name'),
            'episode_number': int_or_none(video.get('shortNumber')),
            'series': show.get('title'),
            'season_number': int_or_none(video.get('season')),
            'duration': int_or_none(video_info.get('duration') or video.get('duration')),
            'release_date': unified_strdate(video.get('releaseDate')),
            'average_rating': float_or_none(video.get('rating') or metas.get('rating')),
            'comment_count': int_or_none(video.get('commentsCount')),
        }


class ADNSeasonIE(ADNBaseIE):
    _VALID_URL = r'https?://(?:www\.)?animationdigitalnetwork\.com/(?:(?P<lang>de)/)?video/(?P<id>\d+)[^/?#]*/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://animationdigitalnetwork.com/video/911-tokyo-mew-mew-new',
        'playlist_count': 12,
        'info_dict': {
            'id': '911',
            'title': 'Tokyo Mew Mew New',
        },
        # 'skip': 'Only available in French end German speaking Europe',
    }]

    def _real_extract(self, url):
        lang, video_show_slug = self._match_valid_url(url).group('lang', 'id')
        self._HEADERS['X-Target-Distribution'] = lang or 'fr'
        show = self._download_json(
            f'{self._API_BASE_URL}show/{video_show_slug}/', video_show_slug,
            'Downloading show JSON metadata', headers=self._HEADERS)['show']
        show_id = str(show['id'])
        episodes = self._download_json(
            f'{self._API_BASE_URL}video/show/{show_id}', video_show_slug,
            'Downloading episode list', headers=self._HEADERS, query={
                'order': 'asc',
                'limit': '-1',
            })

        def entries():
            for episode_id in traverse_obj(episodes, ('videos', ..., 'id', {str_or_none})):
                yield self.url_result(join_nonempty(
                    'https://animationdigitalnetwork.com', lang, 'video',
                    video_show_slug, episode_id, delim='/'), ADNIE, episode_id)

        return self.playlist_result(entries(), show_id, show.get('title'))
