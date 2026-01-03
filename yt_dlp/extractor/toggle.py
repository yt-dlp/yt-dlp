import itertools
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import ExtractorError, determine_ext, int_or_none, parse_iso8601, strip_or_none
from ..utils.traversal import traverse_obj


class ToggleIE(InfoExtractor):
    IE_NAME = 'toggle'
    _VALID_URL = r'(?:https?://(?:(?:www\.)?mewatch|video\.toggle)\.sg/(?:en|zh/)?(?!watch/)(?:[^/]+/)|toggle:)(?:(?:[^#?&]+)(?:/|-))?(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.mewatch.sg/clips/Cuit-Cuit-Clip-6-Warna-Ramadan-2024-450987',
        'info_dict': {
            'id': '450987',
            'title': 'Cuit-Cuit - Clip 6 - Warna Ramadan 2024',
            'description': 'Watch the antics of Mohd Shaqeel and Hanie Bella in Cuit-Cuit. Check out the activities that they do while waiting for break fast. Saksikan gelagat Mohd Shaqeel dan Hanie Bella dalam Cuit-Cuit. Apakah aktiviti yang dilakukan mereka ketika menunggu waktu berbuka?Clip',
            'duration': 68,
            'timestamp': 1712592000,
            'average_rating': 0,
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

    def _extract_episode(self, video_id, meta):
        try:
            info = self._download_json(
                f'{self._API_BASE}/items/{video_id}/videos',
                video_id, 'Downloading video info json',
                query={
                    'delivery': 'stream,progressive',
                    'ff': 'idp,ldp,rpt,cd',
                    'lang': 'en',
                    'resolution': 'External',
                    'segments': 'all',
                })
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 403:
                self.raise_login_required()
            raise

        formats = []
        for video_file in info:
            video_url, vid_format = video_file.get('url'), video_file.get('name')
            if not video_url or video_url == 'NA' or not vid_format:
                continue
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    video_url, video_id, ext='mp4', m3u8_id=vid_format,
                    note=f'Downloading {vid_format} m3u8 information',
                    errnote=f'Failed to download {vid_format} m3u8 information',
                    fatal=False)
                for f in m3u8_formats:
                    formats.append(f)
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    video_url, video_id, mpd_id=vid_format,
                    note=f'Downloading {vid_format} MPD manifest',
                    errnote=f'Failed to download {vid_format} MPD manifest',
                    fatal=False))
            elif ext == 'ism':
                formats.extend(self._extract_ism_formats(
                    video_url, video_id, ism_id=vid_format,
                    note=f'Downloading {vid_format} ISM manifest',
                    errnote=f'Failed to download {vid_format} ISM manifest',
                    fatal=False))

        thumbnails = []
        for _, pic_url in meta.get('images').items():
            if not pic_url:
                continue
            thumbnail = {
                'url': pic_url,
            }
            m = re.search(r'&width=(?P<width>\d+)(?:&height=(?P<height>\d+))?', pic_url, flags=re.IGNORECASE)
            if m:
                thumbnail.update({
                    'width': int(m.group('width')),
                    'height': int(m.group('height')),
                })
            thumbnails.append(thumbnail)

        return {
            'id': video_id,
            'formats': formats,
            'thumbnails': thumbnails,
            **traverse_obj(meta, ({
                'title': ('title'),
                'description': ('description', {strip_or_none}),
                'duration': ('duration', {int_or_none}),
                'timestamp':(('TheatricalReleaseStart', {parse_iso8601}), ('offers', 0, 'startDate', {parse_iso8601})),
                'average_rating': ('totalUserRatings'),
                'is_live': (('type', {str.startswith}, 'channel'), False),
            })),
        }

    def _extract_playlist(self, video_id):
        playlist_meta = self._download_json(
            f'{self._API_BASE}/items/{video_id}',
            video_id,
            query={
                'expand': 'all',
                'segments': 'all',
            })

        def entries(playlist_data):
            season_arg = self._configuration_arg('season_num', casesense=True)
            season_num = int(season_arg[0]) if season_arg else None
            if season_num is not None:
                seasons = traverse_obj(playlist_data, ('seasons', 'items', lambda _, v: v.get('seasonNumber') == season_num))
            else:
                seasons = traverse_obj(playlist_data, ('seasons', 'items'))
            for season in seasons:
                season_title = season.get('title')
                self.write_debug(f'Downloading Season {season_title}')
                season_id = season.get('id')
                for page in itertools.count(1):
                    data = self._download_json(
                        f'{self._API_BASE}/items/{season_id}/children',
                        season_id,
                        note=f'Downloading Season {season_title} page - {page}',
                        query={
                            'ff': 'idp,ldp,rpt,cd',
                            'lang': 'en',
                            'page': page,
                            'page_size': 25,
                            'segments': 'all',
                        })
                    for ep in data.get('items'):
                        yield self._extract_episode(ep.get('id'), ep)
                    if page == traverse_obj(data, ('paging', 'total')):
                        break

        return self.playlist_result(
            entries(playlist_meta), video_id,
            strip_or_none(playlist_meta.get('title')),
            strip_or_none(playlist_meta.get('description')))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._download_json(
            f'{self._API_BASE}/items/{video_id}',
            video_id, 'Downloading video metadata json', query={'segments': 'all'})
        is_drm = (traverse_obj(meta, ('customFields', 'Encryption', {str})))
        if is_drm in ('True', '1', 'true'):
            raise self.report_drm(video_id)
        if meta['type'] not in ('channel', 'movie', 'episode', 'program'):
            return self._extract_playlist(video_id)
        else:
            return self._extract_episode(video_id, meta)


class MeWatchIE(InfoExtractor):
    IE_NAME = 'mewatch'
    _VALID_URL = r'https?://(?:(?:www|live)\.)?mewatch\.sg/watch/[^/?#&]+-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.mewatch.sg/watch/New-Stirrings-E3-Innovation-and-New-Blood-598958',
        'info_dict': {
            'id': '598958',
            'title': 'Ep 3 Innovation and New Blood',
            'description': 'In New Stirrings: Innovation and New Blood, a new generation of hawkers is redefining what it means to cook, create and serve. At Jalan Batu, 24-year-old Fikri Rohaimi, who once worked in Michelin-starred kitchens, now brings restaurant-quality dishes to a hawker stall. At Ghim Moh, Amber Pang\u2019s artisanal bakes bring a breath of fresh air to one of Singapore\u2019s oldest hawker centres. Across the island, robots share the kitchen. From M Plus Fried Rice\u2019s wok hei machine to Steven Lam\u2019s glutinous rice dispenser, they prove that innovation can honour tradition. For others, purpose drives change. Madeline Chan uses her coffee stall to support refugees, while Li Jiali finds healing through pancakes. And through NEA\u2019s Incubation Stall Programme and Social Enterprise Hawker Centres, new hawkers like Jordan Chong and Rick Tan are finding their footing. This episode celebrates how fresh ideas and fearless hearts are keeping Singapore\u2019s hawker spirit alive.',
            'duration': 2810,
            'timestamp': 1767016800,
            'average_rating': 0,
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
