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
            paths = {}
            current = None
            fmt['hls_media_playlist_data'] = ''
            for line in res:
                inf_match = re.match(r'#EXTINF:(\d+)', line)
                if (not current):
                    if (inf_match or line.startswith('#EXT-X-KEY:')):
                        current = {
                            'data': line + '\n',
                            'duration': float(inf_match.group(1)) if inf_match else 0,
                        }
                    else:
                        fmt['hls_media_playlist_data'] += line + '\n'
                elif inf_match:
                    current['duration'] += float(inf_match.group(1))
                    current['data'] += line + '\n'
                elif line.startswith('#'):
                    current['data'] += line + '\n'
                else:
                    # match up to 3 nested paths to avoid including segment specific parts
                    path = re.match(r'(?:/[^/]*){1,3}', urllib.parse.urlparse(urllib.parse.urljoin(base, line)).path or '/').group()
                    current['data'] += line + '\n'
                    if path in paths:
                        paths[path]['data'] += current['data']
                        paths[path]['duration'] += current['duration']
                    else:
                        paths[path] = current
                    current = {'data': '', 'duration': 0}
            longest = max(paths.values(), key=lambda x: x['duration'])
            if (longest):
                fmt['hls_media_playlist_data'] += longest['data'] + current['data']
            else:
                fmt['hls_media_playlist_data'] = None
                self.report_warning(f'Unable to find ad-free playlist in format {fmt.get("format_id")}')

    def _extract_formats(self, video_data):
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(f"{video_data['stitcher']}/v2{video_data['path']}?{video_data['stitcherParams']}&jwt={video_data['sessionToken']}", video_data['id'])
        for f in formats:
            f['url'] += f"&jwt={video_data['sessionToken']}"
            f.setdefault('vcodec', 'avc1.64001f')
            f.setdefault('acodec', 'mp4a.40.2')
            f.setdefault('fps', 30)
        for d in subtitles.values():
            for f in d:
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
        'md5': '966ed552cf5500b23b7eee66b6890cad',
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
            'description': 'md5:2b4a80beff586df77238775a5a67f7bd',
        },
        'playlist_mincount': 113,
    }, {
        'url': 'https://pluto.tv/on-demand/series/66ab6d80b20e79001338fe4c/season/5',
        'info_dict': {
            'id': '66ab6d80b20e79001338fe4c-5',
            'title': 'Squadra Speciale Cobra 11 - Season 5',
        },
        'playlist_count': 17,
    }, {
        'note': 'Video doesn\'t exist, but API returns another one',
        'url': 'https://pluto.tv/it/on-demand/movies/00000000000000000000000000000000',
        'expected_exception': 'ExtractorError',
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
            url_transparent=True,
        )

    def _real_extract(self, url):
        url, video_data = unsmuggle_url(url)
        if video_data:
            return {**self._extract_formats(video_data), 'id': video_data['id']}

        mobj = self._match_valid_url(url).groupdict()
        # here slug may also be the video id, URLs and API accept both
        slug = mobj['slug']
        season_number, episode_id = mobj.get('season'), mobj.get('episode')
        query = {**self._START_QUERY, 'seriesIDs': slug}
        if episode_id:
            query['episodeIDs'] = episode_id

        video_json = self._download_json('https://boot.pluto.tv/v4/start', slug, 'Downloading info json', query=query)
        series = video_json['VOD'][0]

        # sometimes if the link is not valid the API returns a random video as result
        # we have to check if the id is what we expect
        if (series.get('id') or series.get('_id')) != slug and series.get('slug') != slug:
            raise ExtractorError('Failed to find movie or series')

        if episode_id:
            episode = traverse_obj(video_json, ('VOD', 1))
            if not episode or ((episode.get('id') or episode.get('_id')) != episode_id and episode.get('slug') != episode_id):
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
