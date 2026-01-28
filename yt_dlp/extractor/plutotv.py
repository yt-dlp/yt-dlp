import re
import urllib.parse
import uuid

from .common import InfoExtractor
from ..utils import ExtractorError, float_or_none, int_or_none, smuggle_url, traverse_obj, unsmuggle_url


class PlutoTVBase(InfoExtractor):
    _START_QUERY = {
        'appName': 'web',
        'appVersion': 'na',
        'clientID': str(uuid.uuid1()),
        'clientModelNumber': 'na',
        'serverSideAds': 'false',
        'deviceMake': 'unknown',
        'deviceModel': 'web',
        'deviceType': 'web',
        'deviceVersion': 'unknown',
    }

    def _resolve_data(self, start, element):
        return {
            'stitcher': start['servers']['stitcher'],
            'path': element['stitched']['path'],
            'stitcherParams': start['stitcherParams'],
            'sessionToken': start['sessionToken'],
            'id': element.get('id') or element['_id'],
        }

    def _to_ad_free_formats(self, video_id, formats):
        for fmt in formats:
            res, base = self._download_webpage_handle(
                fmt.get('url'), video_id, 'Downloading m3u8 playlist',
                fatal=False)
            if not res:
                continue
            base = base.url
            res = res.splitlines()
            path_occur = {}
            extinf = 0
            for line in res:
                match = re.match(r'^#EXTINF:(\d+)', line)
                if match:
                    extinf = float_or_none(match.group(1)) or 0
                elif not line.startswith('#'):
                    match = re.search(r'^(.+)/[^/]+$', line)
                    if match:
                        path = urllib.parse.urlparse(urllib.parse.urljoin(base, match.group(1))).path
                        path_occur[path] = path_occur.get(path, 0) + extinf
            url_path = max(path_occur, key=path_occur.get)
            if url_path:
                fmt['hls_media_playlist_data'] = ''
                valid = True
                for line in res:
                    # prevent key mismatch
                    if line.startswith('#EXT-X-KEY:'):
                        match = re.search(r'URI="([^"]+)/[^.]+\.key"', line)
                        # if no match, the line is probably malformed, keep it as is
                        valid = not match or urllib.parse.urlparse(urllib.parse.urljoin(base, match.group(1))).path == url_path
                    elif not line.startswith('#'):
                        match = re.search(r'^(.+)/[^/]+$', line)
                        if match:
                            valid = urllib.parse.urlparse(urllib.parse.urljoin(base, match.group(1))).path == url_path
                    if valid:
                        fmt['hls_media_playlist_data'] += line + '\n'
            else:
                self.report_warning(f'Unable to find ad-free playlist in format {fmt.get("format_id")}')

    def _extract_formats(self, video_data):
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(f"{video_data['stitcher']}/v2{video_data['path']}?{video_data['stitcherParams']}&jwt={video_data['sessionToken']}", video_data['id'])
        for f in formats:
            f['url'] += f"&jwt={video_data['sessionToken']}"
            f.setdefault('vcodec', 'avc1.64001f')
            f.setdefault('acodec', 'mp4a.40.2')
            f.setdefault('fps', 30)
        for f in subtitles:
            f['url'] += f"&jwt={video_data['sessionToken']}"
        self._to_ad_free_formats(video_data['id'], formats)
        return {'formats': formats, 'subtitles': subtitles}


class PlutoTVIE(PlutoTVBase):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?pluto\.tv(?:/[^/]+)?/on-demand
        /(movies|series)
        /(?P<slug>[^/]+)
        (?:
            (?:/seasons?/(?P<season>\d+))?
            (?:/episode/(?P<episode>[^/]+))?
        )?'''
    _TESTS = [{
        'url': 'https://pluto.tv/it/on-demand/movies/6246b0adef11000014d220c3',
        'md5': 'f1c7a444e3c05bee8cdb9f28898ffae8',
        'info_dict': {
            'id': '6246b0adef11000014d220c3',
            'ext': 'mp4',
            'episode_id': '6246b0adef11000014d220c3',
            'description': 'md5:c9a412d330d3d73a527e9ba981c0ddb8',
            'episode': 'Non Bussate A Quella Porta',
            'thumbnail': 'http://images.pluto.tv/episodes/6246b0adef11000014d220c3/poster.jpg?fm=png&q=100',
            'display_id': 'dont-knock-twice-it-2016-1-1',
            'genres': ['Horror'],
            'title': 'Non Bussate A Quella Porta',
            'duration': 5940,
        },
    }, {
        'url': 'https://pluto.tv/on-demand/movies/6246b0adef11000014d220c3',
        'only_matching': True,
    }, {
        'url': 'https://pluto.tv/on-demand/series/6655b0c5cceea000134aee27',
        'info_dict': {
            'id': '6655b0c5cceea000134aee27',
            'title': 'Mission Impossible',
            'description': 'md5:21604bf9971528825c359e0f4977d572',
        },
        'playlist_mincount': 113,
    }, {
        'url': 'https://pluto.tv/on-demand/series/66ab6d80b20e79001338fe4c/season/5',
        'info_dict': {
            'id': '66ab6d80b20e79001338fe4c-5',
            'title': 'Squadra Speciale Cobra 11 - Season 5',
        },
        'playlist_count': 17,
    }]

    def _get_video_info(self, video, series=None, season_number=None):
        thumbnails = [{
            'url': cover['url'],
            'width': int(m.group(1)) if (m := re.search(r'w=(\d+)&h=(\d+)', cover['url'])) else None,
            'height': int(m.group(2)) if m else None,
        } for cover in video.get('covers', [])]
        first_cover = traverse_obj(video, ('covers', 0, 'url'))
        if first_cover:
            thumbnails.append({
                'id': 'original',
                'url': re.sub(r'\?.*$', '?fm=png&q=100', first_cover),
                'preference': 1,
            })
        return {
            'id': video.get('id') or video['_id'],
            'title': video.get('name'),
            'display_id': video.get('slug'),
            'thumbnails': thumbnails,
            'description': video.get('description'),
            'duration': float_or_none(video.get('duration'), scale=1000),
            'genres': [video.get('genre')],
            'series_id': series and series.get('id'),
            'series': series and series.get('name'),
            'episode': video.get('name'),
            'episode_id': video.get('id') or video['_id'],
            'season_number': int_or_none(season_number),
        }

    def _playlist_entry(self, video_json, series, season, ep):
        episode_id = ep.get('id') or ep['_id']
        return self.url_result(
            smuggle_url(
                f"https://pluto.tv/on-demand/series/{series.get('id') or series['_id']}/season/{season['number']}/episode/{episode_id}",
                self._resolve_data(video_json, ep),
            ),
            PlutoTVIE,
            episode_id,
            ep.get('name'),
            **self._get_video_info(ep, series, season.get('number')),
        )

    def _real_extract(self, url):
        url, video_data = unsmuggle_url(url)
        if video_data:
            return {**self._extract_formats(video_data), 'id': video_data['id']}

        mobj = self._match_valid_url(url).groupdict()
        slug = mobj['slug']
        season_number, episode_id = mobj.get('season'), mobj.get('episode')
        query = {**self._START_QUERY, 'seriesIDs': slug}
        if episode_id:
            query['episodeIDs'] = episode_id

        video_json = self._download_json('https://boot.pluto.tv/v4/start', slug, 'Downloading info json', query=query)
        series = video_json['VOD'][0]

        if episode_id:
            episode = traverse_obj(video_json, ('VOD', 1))
            if not episode:
                raise ExtractorError('Failed to find episode')
            return {**self._get_video_info(episode, series, season_number), **self._extract_formats(self._resolve_data(video_json, episode))}

        if season_number:
            season = next((s for s in series['seasons'] if s['number'] == int(season_number)), None)
            if not season:
                raise ExtractorError(f'Failed to find season {season_number}')
            return self.playlist_result(
                [self._playlist_entry(video_json, series, season, ep) for ep in season['episodes']],
                f"{series['id']}-{season_number}", f"{series['name']} - Season {season_number}",
            )

        return self.playlist_result(
            [self._playlist_entry(video_json, series, season, ep) for season in series.get('seasons', []) for ep in season['episodes']],
            series['id'], series['name'], series.get('description'),
        ) if 'seasons' in series else {**self._get_video_info(series), **self._extract_formats(self._resolve_data(video_json, series))}
