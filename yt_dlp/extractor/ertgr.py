import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    dict_get,
    int_or_none,
    merge_dicts,
    parse_age_limit,
    parse_iso8601,
    parse_qs,
    str_or_none,
    try_get,
    url_or_none,
    variadic,
)
from ..utils.traversal import traverse_obj


class ERTFlixBaseIE(InfoExtractor):
    def _call_api(
            self, video_id, method='Player/AcquireContent', api_version=1,
            param_headers=None, data=None, headers=None, **params):
        platform_codename = {'platformCodename': 'www'}
        headers_as_param = {'X-Api-Date-Format': 'iso', 'X-Api-Camel-Case': False}
        headers_as_param.update(param_headers or {})
        headers = headers or {}
        if data:
            headers['Content-Type'] = headers_as_param['Content-Type'] = 'application/json;charset=utf-8'
            data = json.dumps(merge_dicts(platform_codename, data)).encode()
        query = merge_dicts(
            {} if data else platform_codename,
            {'$headers': json.dumps(headers_as_param)},
            params)
        response = self._download_json(
            f'https://api.app.ertflix.gr/v{api_version!s}/{method}',
            video_id, fatal=False, query=query, data=data, headers=headers)
        if try_get(response, lambda x: x['Result']['Success']) is True:
            return response

    def _call_api_get_tiles(self, video_id, *tile_ids):
        requested_tile_ids = [video_id, *tile_ids]
        requested_tiles = [{'Id': tile_id} for tile_id in requested_tile_ids]
        tiles_response = self._call_api(
            video_id, method='Tile/GetTiles', api_version=2,
            data={'RequestedTiles': requested_tiles})
        tiles = try_get(tiles_response, lambda x: x['Tiles'], list) or []
        if tile_ids:
            if sorted([tile['Id'] for tile in tiles]) != sorted(requested_tile_ids):
                raise ExtractorError('Requested tiles not found', video_id=video_id)
            return tiles
        try:
            return next(tile for tile in tiles if tile['Id'] == video_id)
        except StopIteration:
            raise ExtractorError('No matching tile found', video_id=video_id)


class ERTFlixCodenameIE(ERTFlixBaseIE):
    IE_NAME = 'ertflix:codename'
    IE_DESC = 'ERTFLIX videos by codename'
    _VALID_URL = r'ertflix:(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'ertflix:monogramma-praxitelis-tzanoylinos',
        'md5': '5b9c2cd171f09126167e4082fc1dd0ef',
        'info_dict': {
            'id': 'monogramma-praxitelis-tzanoylinos',
            'ext': 'mp4',
            'title': 'md5:ef0b439902963d56c43ac83c3f41dd0e',
        },
    },
    ]

    def _extract_formats_and_subs(self, video_id):
        media_info = self._call_api(video_id, codename=video_id)
        formats, subtitles = [], {}
        for media in traverse_obj(media_info, (
                'MediaFiles', lambda _, v: v['RoleCodename'] == 'main',
                'Formats', lambda _, v: url_or_none(v['Url']))):
            fmt_url = media['Url']
            ext = determine_ext(fmt_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    fmt_url, video_id, m3u8_id='hls', ext='mp4', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    fmt_url, video_id, mpd_id='dash', fatal=False)
            else:
                formats.append({
                    'url': fmt_url,
                    'format_id': str_or_none(media.get('Id')),
                })
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return formats, subtitles

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats, subs = self._extract_formats_and_subs(video_id)

        if formats:
            return {
                'id': video_id,
                'formats': formats,
                'subtitles': subs,
                'title': self._generic_title(url),
            }


class ERTFlixIE(ERTFlixBaseIE):
    IE_NAME = 'ertflix'
    IE_DESC = 'ERTFLIX videos'
    _VALID_URL = r'https?://www\.ertflix\.gr/(?:[^/]+/)?(?:series|vod)/(?P<id>[a-z]{3}\.\d+)'
    _TESTS = [{
        'url': 'https://www.ertflix.gr/vod/vod.173258-aoratoi-ergates',
        'md5': '6479d5e60fd7e520b07ba5411dcdd6e7',
        'info_dict': {
            'id': 'aoratoi-ergates',
            'ext': 'mp4',
            'title': 'md5:c1433d598fbba0211b0069021517f8b4',
            'description': 'md5:01a64d113c31957eb7eb07719ab18ff4',
            'thumbnail': r're:https?://.+\.jpg',
            'episode_id': 'vod.173258',
            'timestamp': 1639648800,
            'upload_date': '20211216',
            'duration': 3166,
            'age_limit': 8,
        },
    }, {
        'url': 'https://www.ertflix.gr/series/ser.3448-monogramma',
        'info_dict': {
            'id': 'ser.3448',
            'age_limit': 8,
            'description': 'Η εκπομπή σαράντα ετών που σημάδεψε τον πολιτισμό μας.',
            'title': 'Μονόγραμμα',
        },
        'playlist_mincount': 64,
    }, {
        'url': 'https://www.ertflix.gr/series/ser.3448-monogramma?season=1',
        'info_dict': {
            'id': 'ser.3448',
            'age_limit': 8,
            'description': 'Η εκπομπή σαράντα ετών που σημάδεψε τον πολιτισμό μας.',
            'title': 'Μονόγραμμα',
        },
        'playlist_count': 22,
    }, {
        'url': 'https://www.ertflix.gr/series/ser.3448-monogramma?season=1&season=2021%20-%202022',
        'info_dict': {
            'id': 'ser.3448',
            'age_limit': 8,
            'description': 'Η εκπομπή σαράντα ετών που σημάδεψε τον πολιτισμό μας.',
            'title': 'Μονόγραμμα',
        },
        'playlist_mincount': 36,
    }, {
        'url': 'https://www.ertflix.gr/series/ser.164991-to-diktuo-1?season=1-9',
        'info_dict': {
            'id': 'ser.164991',
            'age_limit': 8,
            'description': 'Η πρώτη ελληνική εκπομπή με θεματολογία αποκλειστικά γύρω από το ίντερνετ.',
            'title': 'Το δίκτυο',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://www.ertflix.gr/en/vod/vod.127652-ta-kalytera-mas-chronia-ep1-mia-volta-sto-feggari',
        'only_matching': True,
    }]

    def _extract_episode(self, episode):
        codename = try_get(episode, lambda x: x['Codename'], str)
        title = episode.get('Title')
        description = clean_html(dict_get(episode, ('ShortDescription', 'TinyDescription')))
        if not codename or not title or not episode.get('HasPlayableStream', True):
            return
        thumbnail = next((
            url_or_none(thumb.get('Url'))
            for thumb in variadic(dict_get(episode, ('Images', 'Image')) or {})
            if thumb.get('IsMain')),
            None)
        return {
            '_type': 'url_transparent',
            'thumbnail': thumbnail,
            'id': codename,
            'episode_id': episode.get('Id'),
            'title': title,
            'alt_title': episode.get('Subtitle'),
            'description': description,
            'timestamp': parse_iso8601(episode.get('PublishDate')),
            'duration': episode.get('DurationSeconds'),
            'age_limit': self._parse_age_rating(episode),
            'url': f'ertflix:{codename}',
        }

    @staticmethod
    def _parse_age_rating(info_dict):
        return parse_age_limit(
            info_dict.get('AgeRating')
            or (info_dict.get('IsAdultContent') and 18)
            or (info_dict.get('IsKidsContent') and 0))

    def _extract_series(self, video_id, season_titles=None, season_numbers=None):
        media_info = self._call_api(video_id, method='Tile/GetSeriesDetails', id=video_id)

        series = try_get(media_info, lambda x: x['Series'], dict) or {}
        series_info = {
            'age_limit': self._parse_age_rating(series),
            'title': series.get('Title'),
            'description': dict_get(series, ('ShortDescription', 'TinyDescription')),
        }
        if season_numbers:
            season_titles = season_titles or []
            for season in try_get(series, lambda x: x['Seasons'], list) or []:
                if season.get('SeasonNumber') in season_numbers and season.get('Title'):
                    season_titles.append(season['Title'])

        def gen_episode(m_info, season_titles):
            for episode_group in try_get(m_info, lambda x: x['EpisodeGroups'], list) or []:
                if season_titles and episode_group.get('Title') not in season_titles:
                    continue
                episodes = try_get(episode_group, lambda x: x['Episodes'], list)
                if not episodes:
                    continue
                season_info = {
                    'season': episode_group.get('Title'),
                    'season_number': int_or_none(episode_group.get('SeasonNumber')),
                }
                try:
                    episodes = [(int(ep['EpisodeNumber']), ep) for ep in episodes]
                    episodes.sort()
                except (KeyError, ValueError):
                    episodes = enumerate(episodes, 1)
                for n, episode in episodes:
                    info = self._extract_episode(episode)
                    if info is None:
                        continue
                    info['episode_number'] = n
                    info.update(season_info)
                    yield info

        return self.playlist_result(
            gen_episode(media_info, season_titles), playlist_id=video_id, **series_info)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if video_id.startswith('ser.'):
            param_season = parse_qs(url).get('season', [None])
            param_season = [
                (have_number, int_or_none(v) if have_number else str_or_none(v))
                for have_number, v in
                [(int_or_none(ps) is not None, ps) for ps in param_season]
                if v is not None
            ]
            season_kwargs = {
                k: [v for is_num, v in param_season if is_num is c] or None
                for k, c in
                [('season_titles', False), ('season_numbers', True)]
            }
            return self._extract_series(video_id, **season_kwargs)

        return self._extract_episode(self._call_api_get_tiles(video_id))


class ERTWebtvEmbedIE(InfoExtractor):
    IE_NAME = 'ertwebtv:embed'
    IE_DESC = 'ert.gr webtv embedded videos'
    _BASE_PLAYER_URL_RE = re.escape('//www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php')
    _VALID_URL = rf'https?:{_BASE_PLAYER_URL_RE}\?([^#]+&)?f=(?P<id>[^#&]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+?src=(?P<_q1>["\'])(?P<url>(?:https?:)?{_BASE_PLAYER_URL_RE}\?(?:(?!(?P=_q1)).)+)(?P=_q1)']

    _TESTS = [{
        'url': 'https://www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php?f=trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4&bgimg=/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg',
        'md5': 'f9e9900c25c26f4ecfbddbb4b6305854',
        'info_dict': {
            'id': 'trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4',
            'title': 'md5:914f06a73cd8b62fbcd6fb90c636e497',
            'ext': 'mp4',
            'thumbnail': 'https://program.ert.gr/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            f'https://mediastream.ert.gr/vodedge/_definst_/mp4:dvrorigin/{video_id}/playlist.m3u8',
            video_id, 'mp4')
        thumbnail_id = parse_qs(url).get('bgimg', [None])[0]
        if thumbnail_id and not thumbnail_id.startswith('http'):
            thumbnail_id = f'https://program.ert.gr{thumbnail_id}'
        return {
            'id': video_id,
            'title': f'VOD - {video_id}',
            'thumbnail': thumbnail_id,
            'formats': formats,
            'subtitles': subs,
        }
