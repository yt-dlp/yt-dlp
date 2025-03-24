import json
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    filter_dict,
    float_or_none,
    join_nonempty,
    mimetype2ext,
    parse_iso8601,
    unsmuggle_url,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class StreaksBaseIE(InfoExtractor):
    _API_URL_TEMPLATE = 'https://{}.api.streaks.jp/v1/projects/{}/medias/{}{}'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']

    def _extract_from_streaks_api(self, project_id, media_id, headers=None, query=None, ssai=False):
        try:
            response = self._download_json(
                self._API_URL_TEMPLATE.format('playback', project_id, media_id, ''),
                media_id, 'Downloading STREAKS playback API JSON', headers={
                    'Accept': 'application/json',
                    'Origin': 'https://players.streaks.jp',
                    **self.geo_verification_headers(),
                    **(headers or {}),
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in {403, 404}:
                error = self._parse_json(e.cause.response.read().decode(), media_id, fatal=False)
                message = traverse_obj(error, ('message', {str}))
                code = traverse_obj(error, ('code', {str}))
                if code == 'REQUEST_FAILED':
                    self.raise_geo_restricted(message, countries=self._GEO_COUNTRIES)
                elif code == 'MEDIA_NOT_FOUND':
                    raise ExtractorError(message, expected=True)
                elif code or message:
                    raise ExtractorError(join_nonempty(code, message, delim=': '))
            raise

        streaks_id = response['id']
        live_status = {
            'clip': 'was_live',
            'file': 'not_live',
            'linear': 'is_live',
            'live': 'is_live',
        }.get(response.get('type'))

        formats, subtitles = [], {}
        drm_formats = False

        for source in traverse_obj(response, ('sources', lambda _, v: v['src'])):
            if source.get('key_systems'):
                drm_formats = True
                continue

            src_url = source['src']
            is_live = live_status == 'is_live'
            ext = mimetype2ext(source.get('type'))
            if ext != 'm3u8':
                self.report_warning(f'Unsupported stream type: {ext}')
                continue

            if is_live and ssai:
                session_params = traverse_obj(self._download_json(
                    self._API_URL_TEMPLATE.format('ssai', project_id, streaks_id, '/ssai/session'),
                    media_id, 'Downloading session parameters',
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                    data=json.dumps({'id': source['id']}).encode(),
                ), (0, 'query', {urllib.parse.parse_qs}))
                src_url = update_url_query(src_url, session_params)

            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                src_url, media_id, 'mp4', m3u8_id='hls', fatal=False, live=is_live, query=query)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if not formats and drm_formats:
            self.report_drm(media_id)
        self._remove_duplicate_formats(formats)

        for subs in traverse_obj(response, (
            'tracks', lambda _, v: v['kind'] in ('captions', 'subtitles') and url_or_none(v['src']),
        )):
            lang = traverse_obj(subs, ('srclang', {str.lower})) or 'ja'
            subtitles.setdefault(lang, []).append({'url': subs['src']})

        return {
            'id': streaks_id,
            'display_id': media_id,
            'formats': formats,
            'live_status': live_status,
            'subtitles': subtitles,
            'uploader_id': project_id,
            **traverse_obj(response, {
                'title': ('name', {str}),
                'description': ('description', {str}, filter),
                'duration': ('duration', {float_or_none}),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
                'tags': ('tags', ..., {str}),
                'thumbnails': (('poster', 'thumbnail'), 'src', {'url': {url_or_none}}),
                'timestamp': ('created_at', {parse_iso8601}),
            }),
        }


class StreaksIE(StreaksBaseIE):
    _VALID_URL = [
        r'https?://players\.streaks\.jp/(?P<project_id>[\w-]+)/[\da-f]+/index\.html\?(?:[^#]+&)?m=(?P<id>(?:ref:)?[\w-]+)',
        r'https?://playback\.api\.streaks\.jp/v1/projects/(?P<project_id>[\w-]+)/medias/(?P<id>(?:ref:)?[\w-]+)',
    ]
    _EMBED_REGEX = [rf'<iframe\s+[^>]*\bsrc\s*=\s*["\'](?P<url>{_VALID_URL[0]})']
    _TESTS = [{
        'url': 'https://players.streaks.jp/tipness/08155cd19dc14c12bebefb69b92eafcc/index.html?m=dbdf2df35b4d483ebaeeaeb38c594647',
        'info_dict': {
            'id': 'dbdf2df35b4d483ebaeeaeb38c594647',
            'ext': 'mp4',
            'title': '3shunenCM_edit.mp4',
            'display_id': 'dbdf2df35b4d483ebaeeaeb38c594647',
            'duration': 47.533,
            'live_status': 'not_live',
            'modified_date': '20230726',
            'modified_timestamp': 1690356180,
            'timestamp': 1690355996,
            'upload_date': '20230726',
            'uploader_id': 'tipness',
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
            'modified_date': '20250310',
            'modified_timestamp': 1741586302,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1741585839,
            'upload_date': '20250310',
            'uploader_id': 'ktv-web',
        },
    }, {
        'url': 'https://playback.api.streaks.jp/v1/projects/ktv-web/medias/b5411938e1e5435dac71edf829dd4813',
        'info_dict': {
            'id': 'b5411938e1e5435dac71edf829dd4813',
            'ext': 'mp4',
            'title': 'KANTELE_SYUSEi_0630',
            'display_id': 'b5411938e1e5435dac71edf829dd4813',
            'live_status': 'not_live',
            'modified_date': '20250122',
            'modified_timestamp': 1737522999,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1735205137,
            'upload_date': '20241226',
            'uploader_id': 'ktv-web',
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
            'modified_date': '20240805',
            'modified_timestamp': 1722896263,
            'timestamp': 1722777618,
            'upload_date': '20240804',
            'uploader_id': 'tver-olympic',
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
            'modified_date': '20241031',
            'modified_timestamp': 1730339858,
            'timestamp': 1705466840,
            'upload_date': '20240117',
            'uploader_id': 'tbs',
        },
    }, {
        # DRM protected
        'url': 'https://players.streaks.jp/sp-jbc/a12d7ee0f40c49d6a0a2bff520639677/index.html?m=5f89c62f37ee4a68be8e6e3b1396c7d8',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://event.play.jp/playnext2023/',
        'info_dict': {
            'id': '2d975178293140dc8074a7fc536a7604',
            'ext': 'mp4',
            'title': 'PLAY NEXTキームービー（本番）',
            'uploader_id': 'play',
            'duration': 17.05,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1668387517,
            'upload_date': '20221114',
            'modified_timestamp': 1739411523,
            'modified_date': '20250213',
            'live_status': 'not_live',
        },
    }, {
        'url': 'https://wowshop.jp/Page/special/cooking_goods/?bid=wowshop&srsltid=AfmBOor_phUNoPEE_UCPiGGSCMrJE5T2US397smvsbrSdLqUxwON0el4',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '?bid=wowshop&srsltid=AfmBOor_phUNoPEE_UCPiGGSCMrJE5T2US397smvsbrSdLqUxwON0el4',
            'title': 'ワンランク上の料理道具でとびきりの“おいしい”を食卓へ｜wowshop',
            'description': 'md5:914b5cb8624fc69274c7fb7b2342958f',
            'age_limit': 0,
            'thumbnail': 'https://wowshop.jp/Page/special/cooking_goods/images/ogp.jpg',
        },
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        project_id, media_id = self._match_valid_url(url).group('project_id', 'id')

        return self._extract_from_streaks_api(
            project_id, media_id, headers=filter_dict({
                'X-Streaks-Api-Key': smuggled_data.get('api_key'),
            }))
