import json
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    filter_dict,
    float_or_none,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class StreaksBaseIE(InfoExtractor):
    _API_URL_TEMPLATE = 'https://{}.api.streaks.jp/v1/projects/{}/medias/{}{}'
    _GEO_COUNTRIES = ['JP']

    def _parse_streaks_metadata(self, project_id, media_id, headers=None, query=None, ssai=False):
        try:
            streaks = self._download_json(
                self._API_URL_TEMPLATE.format('playback', project_id, media_id, ''),
                media_id, headers=filter_dict({
                    'Content-Type': 'application/json',
                    'Origin': 'https://players.streaks.jp',
                    **self.geo_verification_headers(),
                } | (headers or {})),
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in {403, 404}:
                error = self._parse_json(e.cause.response.read().decode(), media_id)
                message = error.get('message')
                if error.get('code') == 'REQUEST_FAILED':
                    self.raise_geo_restricted(message, self._GEO_COUNTRIES)
                elif error.get('code') == 'MEDIA_NOT_FOUND':
                    raise ExtractorError(message, expected=True)
                raise ExtractorError(message)
            raise

        live_status = {
            'clip': 'was_live',
            'file': 'not_live',
            'linear': 'is_live',
            'live': 'is_live',
        }[streaks['type']]

        formats, subtitles = [], {}
        for source in streaks.get('sources', []):
            ext = mimetype2ext(source.get('type'))
            if src := source.get('src'):
                if ext == 'm3u8':
                    if is_live := live_status == 'is_live' and ssai:
                        session = dict(traverse_obj(self._download_json(
                            self._API_URL_TEMPLATE.format(
                                'ssai', project_id, streaks['id'], '/ssai/session'),
                            media_id, headers={
                                'Content-Type': 'application/json',
                            }, data=json.dumps({
                                'id': streaks['sources'][0]['id'],
                            }).encode(),
                        ), (0, 'query', {urllib.parse.parse_qsl})))
                        src = update_url_query(src, session)

                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        src, media_id, 'mp4', m3u8_id='hls',
                        fatal=False, live=is_live, query=query or {})
                elif ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        src, media_id, mpd_id='dash', fatal=False)
                else:
                    raise ExtractorError(f'Unsupported type: {ext}')
            if source.get('key_systems'):
                for f in fmts:
                    f['has_drm'] = True
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._remove_duplicate_formats(formats)
        if not formats:
            self.raise_no_formats('This content is currently unavailable', True, media_id)

        for track in streaks.get('tracks', []):
            if track.get('kind') == 'subtitles' and (src := traverse_obj(track, ('src', {url_or_none}))):
                lang = (track.get('srclang') or 'ja').lower()
                subtitles.setdefault(lang, []).append({'url': src})

        return {
            'display_id': media_id,
            'formats': formats,
            'live_status': live_status,
            'subtitles': subtitles,
            **traverse_obj(streaks, {
                'id': (('id', ('ref_id', {lambda x: f'ref:{x}'})), {str_or_none}, filter, any),
                'title': ('name', {str}),
                'channel_id': ('channel_id', {str_or_none}),
                'description': ('description', {str}, filter),
                'duration': ('duration', {float_or_none}),
                'episode_id': ('program_id', {str_or_none}),
                'tags': ('tags', ..., {str}),
                'thumbnail': (('poster', 'thumbnail'), 'src', {url_or_none}, any),
                'timestamp': ('updated_at', {parse_iso8601}),
                'uploader': ('project_id', {str_or_none}),
            }),
        }


class StreaksIE(StreaksBaseIE):
    IE_NAME = 'streaks'
    IE_DESC = 'STREAKS'

    _VALID_URL = [
        r'https?://players\.streaks\.jp/(?P<project_id>[\w-]+)/(?P<uploader_id>\w+)/index\.html\?m=(?P<media_id>(?:ref:)?[\w-]+)',
        r'https?://playback\.api\.streaks\.jp/v1/projects/(?P<project_id>[\w-]+)/medias/(?P<media_id>(?:ref:)?[\w-]+)',
    ]
    _TESTS = [{
        'url': 'https://players.streaks.jp/tipness/08155cd19dc14c12bebefb69b92eafcc/index.html?m=dbdf2df35b4d483ebaeeaeb38c594647',
        'info_dict': {
            'id': 'dbdf2df35b4d483ebaeeaeb38c594647',
            'ext': 'mp4',
            'title': '3shunenCM_edit.mp4',
            'display_id': 'dbdf2df35b4d483ebaeeaeb38c594647',
            'duration': 47.533,
            'live_status': 'not_live',
            'timestamp': 1690356180,
            'upload_date': '20230726',
            'uploader': 'tipness',
            'uploader_id': '08155cd19dc14c12bebefb69b92eafcc',
        },
    }, {
        'url': 'https://players.streaks.jp/ktv-web/0298e8964c164ab384c07ef6e08c444b/index.html?m=ref:mycoffeetime_250317',
        'info_dict': {
            'id': 'dccdc079e3fd41f88b0c8435e2d453ab',
            'ext': 'mp4',
            'title': 'わたしの珈琲時間_250317',
            'display_id': 'ref:mycoffeetime_250317',
            'duration': 122.99,
            'live_status': 'not_live',
            'thumbnail': r're:https://.+\.jpg',
            'timestamp': 1741586302,
            'upload_date': '20250310',
            'uploader': 'ktv-web',
            'uploader_id': '0298e8964c164ab384c07ef6e08c444b',
        },
    }, {
        'url': 'https://players.streaks.jp/sp-jbc/a12d7ee0f40c49d6a0a2bff520639677/index.html?m=5f89c62f37ee4a68be8e6e3b1396c7d8',
        'info_dict': {
            'id': '5f89c62f37ee4a68be8e6e3b1396c7d8',
            'ext': 'mp4',
            'title': '30715小田井涼平のあい旅＃５８.mp4',
            'display_id': '5f89c62f37ee4a68be8e6e3b1396c7d8',
            'duration': 3420.017,
            'live_status': 'not_live',
            'timestamp': 1710741433,
            'upload_date': '20240318',
            'uploader': 'sp-jbc',
            'uploader_id': 'a12d7ee0f40c49d6a0a2bff520639677',
        },
        'skip': 'DRM Protected',
    }, {
        'url': 'https://playback.api.streaks.jp/v1/projects/ytv-news/medias/97d7a6da69e746b6aa6757e9298f0c55',
        'info_dict': {
            'id': '97d7a6da69e746b6aa6757e9298f0c55',
            'ext': 'mp4',
            'title': '225be9f3-ea14-4052-9b68-4de29366bfde.mp4',
            'display_id': '97d7a6da69e746b6aa6757e9298f0c55',
            'duration': 44.586,
            'live_status': 'not_live',
            'thumbnail': r're:https://.+\.jpg',
            'timestamp': 1682407390,
            'uploader': 'ytv-news',
            'upload_date': '20230425',
        },
    }, {
        # TVer Olympics: website already down, but api remains accessible
        'url': 'https://playback.api.streaks.jp/v1/projects/tver-olympic/medias/ref:sp_240806_1748_dvr',
        'info_dict': {
            'id': 'c10f7345adb648cf804d7578ab93b2e3',
            'ext': 'mp4',
            'title': 'サッカー 男子 準決勝_dvr',
            'display_id': 'ref:sp_240806_1748_dvr',
            'duration': 12960.0,
            'live_status': 'was_live',
            'timestamp': 1722896263,
            'uploader': 'tver-olympic',
            'upload_date': '20240805',
        },
    }, {
        # TBS FREE: 24-hour stream
        'url': 'https://playback.api.streaks.jp/v1/projects/tbs/medias/ref:simul-02',
        'info_dict': {
            'id': 'c4e83a7b48f4409a96adacec674b4e22',
            'ext': 'mp4',
            'title': str,
            'display_id': 'ref:simul-02',
            'live_status': 'is_live',
            'timestamp': 1730339858,
            'uploader': 'tbs',
            'upload_date': '20241031',
        },
    }]

    def _real_extract(self, url):
        match = self._match_valid_url(url).groupdict()
        project_id, uploader_id, media_id = (
            match.get(k) for k in ('project_id', 'uploader_id', 'media_id'))

        return {
            **self._parse_streaks_metadata(project_id, media_id, headers={
                'X-Streaks-Api-Key': self._configuration_arg('x_streaks_api_key', [None])[0],
            }),
            'uploader_id': uploader_id if uploader_id else None,
        }
