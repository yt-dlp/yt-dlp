import itertools
import operator

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_iso8601,
    parse_qs,
    str_or_none,
    strip_or_none,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ToggleIE(InfoExtractor):
    IE_NAME = 'toggle'
    _VALID_URL = r'(?:https?://(?:(?:www\.)?mewatch|video\.toggle)\.sg/(?:en|zh/)?(?!watch/)(?:[^/]+/)|toggle:)(?:(?:[^#?&]+)(?:/|-))?(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.mewatch.sg/clips/Cuit-Cuit-Clip-6-Warna-Ramadan-2024-450987',
        'info_dict': {
            'id': '450987',
            'ext': 'mp4',
            'title': 'Cuit-Cuit - Clip 6 - Warna Ramadan 2024',
            'description': 'md5:786469cb5fd4d479ae80976052a3ee43',
            'average_rating': 0,
            'duration': 68,
            'thumbnail': r're:https://(?:[^.]+\.)?togglestatic\.com/shain/v1/dataservice/ResizeImage/.+',
            'upload_date': '20240408',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mewatch.sg/show/New-Stirrings-598293',
        'info_dict': {
            'id': '598293',
            'title': 'New Stirrings',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.mewatch.sg/movie/The-White-Storm-3-Heaven-Or-Hell-589395',
        'only_matching': True,
    }, {
        'url': 'https://www.mewatch.sg/channels/oktolidays/186574',
        'only_matching': True,
    }]
    _API_BASE = 'https://cdn.mewatch.sg/api'

    def _call_api(self, item_id, endpoint, query=None, **kwargs):
        query = {'segments': 'all', **(query or {})}
        return self._download_json(f'{self._API_BASE}/items/{endpoint}', item_id, query=query, **kwargs)

    def _extract_episode(self, video_id, meta, fatal=False):
        info = self._call_api(video_id, f'{video_id}/videos', query={'delivery': 'stream,progressive', 'resolution': 'External'}, expected_status=403)

        if isinstance(info, dict):
            msg = info.get('message')
            if not fatal:
                self.report_warning(f'Unable to extract info for episode {video_id} api says: {msg}')
                return {}
            raise ExtractorError(msg, expected='permitted' in msg)

        formats = []
        for video_url, vid_format in traverse_obj(info, (
                lambda _, v: (v.get('url') or 'NA') != 'NA' and v.get('name'),
                {operator.itemgetter('url', 'name')},
                {lambda x: x if len(x) == 2 and all(x) else None},
        )):
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                fmts = self._extract_m3u8_formats(
                    video_url, video_id, ext='mp4', m3u8_id=vid_format,
                    note=f'Downloading {vid_format} m3u8 information',
                    errnote=f'Failed to download {vid_format} m3u8 information', fatal=False)
            elif ext == 'mpd':
                fmts = self._extract_mpd_formats(
                    video_url, video_id, mpd_id=vid_format,
                    note=f'Downloading {vid_format} MPD manifest',
                    errnote=f'Failed to download {vid_format} MPD manifest',
                    fatal=False)
            elif ext == 'ism':
                fmts = self._extract_ism_formats(
                    video_url, video_id, ism_id=vid_format,
                    note=f'Downloading {vid_format} ISM manifest',
                    errnote=f'Failed to download {vid_format} ISM manifest',
                    fatal=False)
            formats.extend(fmts)

        subtitles = {}
        for sub in traverse_obj(info,(lambda _, x: x.get('subtitlesCollection'), 'subtitlesCollection', lambda _, x: x.get('url'))):
            url = sub.get('url')
            subtitles.setdefault(sub.get('languageCode', 'en'), []).append({
                'url': url,
                'ext': determine_ext(url),
            })

        return {
            'id': video_id,
            **traverse_obj(meta, ({
                'title': ('title', {str_or_none}),
                'description': ('description', {strip_or_none}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('TheatricalReleaseStart', {parse_iso8601}),
                'upload_date': ('offers', 0, 'startDate', {unified_strdate}),
                'average_rating': ('totalUserRatings', {int_or_none}),
                'is_live': ('type', {lambda x: x.startswith('channel')}),
                'thumbnails': (
                    'images', ..., {
                        'url': {url_or_none},
                        'width': ({str.lower}, {parse_qs}, 'width', -1, {int_or_none}),
                        'height': ({str.lower}, {parse_qs}, 'height', -1, {int_or_none}),
                    }),
            })),
            'formats': formats,
            'subtitles': subtitles,
        }

    def _extract_playlist(self, video_id, playlist_meta):
        def entries(playlist_data):
            for season in traverse_obj(playlist_data, ('seasons', 'items')):
                season_title = season.get('title')
                season_id = season.get('id')
                for page_num in itertools.count(1):
                    page = self._call_api(
                        season_id,
                        f'{season_id}/children',
                        note=f'Downloading Season {season_title} page - {page_num}',
                        query={
                            'order': 'asc',
                            'page': page_num,
                            'page_size': 25,
                        })
                    for ep in page.get('items'):
                        yield self._extract_episode(ep.get('id'), ep)
                    if page_num == traverse_obj(page, ('paging', 'total')):
                        break

        return self.playlist_result(entries(playlist_meta), video_id, **traverse_obj(playlist_meta, {
            'title': ('title', {strip_or_none}),
            'description': ('description', {strip_or_none}),
        }))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._call_api(video_id, video_id, query={'expand': 'all'})
        is_drm = traverse_obj(meta, ('customFields', 'Encryption', {str.lower}), default='')
        if is_drm == 'true':
            raise self.report_drm(video_id)
        if meta['type'] not in ('channel', 'movie', 'episode', 'program'):
            return self._extract_playlist(video_id, meta)
        return self._extract_episode(video_id, meta, fatal=True)


class MeWatchIE(InfoExtractor):
    IE_NAME = 'mewatch'
    _VALID_URL = r'https?://(?:(?:www|live)\.)?mewatch\.sg/watch/[^/?#&]+-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.mewatch.sg/watch/New-Stirrings-E3-Innovation-and-New-Blood-598958',
        'info_dict': {
            'id': '598958',
            'ext': 'mp4',
            'title': 'Ep 3 Innovation and New Blood',
            'description': 'md5:7f7af43b79465be2961f8277a980c1a0',
            'average_rating': 0,
            'duration': 2810,
            'thumbnail': r're:https://(?:[^.]+\.)?togglestatic\.com/shain/v1/dataservice/ResizeImage/.+',
            'upload_date': '20251229',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mewatch.sg/watch/Sunny-Again-Tomorrow-E2-589705',
        'only_matching': True,
    }, {
        'url': 'https://www.mewatch.sg/watch/We-Are-Number-1-(Mandarin-dubbed)-E1-589860',
        'only_matching': True,
    }, {
        'url': 'https://www.mewatch.sg/watch/The-White-Storm-3-Heaven-Or-Hell-589395',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        item_id = self._match_id(url)
        return self.url_result(
            'toggle:' + item_id, ToggleIE.ie_key(), item_id)
