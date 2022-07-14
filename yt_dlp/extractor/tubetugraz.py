from .common import InfoExtractor
from ..utils import (
    float_or_none,
    parse_resolution,
    traverse_obj,
    urlencode_postdata,
    variadic,
)


class TubeTuGrazBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'tubetugraz'

    _API_EPISODE = 'https://tube.tugraz.at/search/episode.json'
    _FORMAT_TYPES = ('presentation', 'presenter')

    def _perform_login(self, username, password):
        urlh = self._request_webpage(
            'https://tube.tugraz.at/Shibboleth.sso/Login?target=/paella/ui/index.html',
            None, fatal=False, note='downloading login page', errnote='unable to fetch login page')
        if not urlh:
            return

        urlh = self._request_webpage(
            urlh.geturl(), None, fatal=False, headers={'referer': urlh.geturl()},
            note='logging in', errnote='unable to log in', data=urlencode_postdata({
                'lang': 'de',
                '_eventId_proceed': '',
                'j_username': username,
                'j_password': password
            }))

        if urlh and urlh.geturl() != 'https://tube.tugraz.at/paella/ui/index.html':
            self.report_warning('unable to login: incorrect password')

    def _extract_episode(self, episode_info):
        id = episode_info.get('id')
        formats = list(self._extract_formats(
            traverse_obj(episode_info, ('mediapackage', 'media', 'track')), id))
        self._sort_formats(formats)

        title = traverse_obj(episode_info, ('mediapackage', 'title'), 'dcTitle')
        series_title = traverse_obj(episode_info, ('mediapackage', 'seriestitle'))
        creator = ', '.join(variadic(traverse_obj(
            episode_info, ('mediapackage', 'creators', 'creator'), 'dcCreator', default='')))
        return {
            'id': id,
            'title': title,
            'creator': creator or None,
            'duration': traverse_obj(episode_info, ('mediapackage', 'duration'), 'dcExtent'),
            'series': series_title,
            'series_id': traverse_obj(episode_info, ('mediapackage', 'series'), 'dcIsPartOf'),
            'episode': series_title and title,
            'formats': formats
        }

    def _set_format_type(self, formats, type):
        for f in formats:
            f['format_note'] = type
            if not type.startswith(self._FORMAT_TYPES[0]):
                f['preference'] = -2
        return formats

    def _extract_formats(self, format_list, id):
        has_hls, has_dash = False, False

        for format_info in format_list or []:
            url = traverse_obj(format_info, ('tags', 'url'), 'url')
            if url is None:
                continue

            type = format_info.get('type') or 'unknown'
            transport = (format_info.get('transport') or 'https').lower()

            if transport == 'https':
                formats = [{
                    'url': url,
                    'abr': float_or_none(traverse_obj(format_info, ('audio', 'bitrate')), 1000),
                    'vbr': float_or_none(traverse_obj(format_info, ('video', 'bitrate')), 1000),
                    'fps': traverse_obj(format_info, ('video', 'framerate')),
                    **parse_resolution(traverse_obj(format_info, ('video', 'resolution'))),
                }]
            elif transport == 'hls':
                has_hls, formats = True, self._extract_m3u8_formats(
                    url, id, 'mp4', fatal=False, note=f'downloading {type} HLS manifest')
            elif transport == 'dash':
                has_dash, formats = True, self._extract_mpd_formats(
                    url, id, fatal=False, note=f'downloading {type} DASH manifest')
            else:
                # RTMP, HDS, SMOOTH, and unknown formats
                # - RTMP url fails on every tested entry until now
                # - HDS url 404's on every tested entry until now
                # - SMOOTH url 404's on every tested entry until now
                continue

            yield from self._set_format_type(formats, type)

        # TODO: Add test for these
        for type in self._FORMAT_TYPES:
            if not has_hls:
                hls_formats = self._extract_m3u8_formats(
                    f'https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_{id}_{type}.smil/playlist.m3u8',
                    id, 'mp4', fatal=False, note=f'Downloading {type} HLS manifest', errnote=False) or []
                yield from self._set_format_type(hls_formats, type)

            if not has_dash:
                dash_formats = self._extract_mpd_formats(
                    f'https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_{id}_{type}.smil/manifest_mpm4sav_mvlist.mpd',
                    id, fatal=False, note=f'Downloading {type} DASH manifest', errnote=False)
                yield from self._set_format_type(dash_formats, type)


class TubeTuGrazIE(TubeTuGrazBaseIE):
    IE_DESC = 'tube.tugraz.at'

    _VALID_URL = r'''(?x)
        https?://tube\.tugraz\.at/paella/ui/watch.html\?id=
        (?P<id>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})
    '''
    _TESTS = [{
        'url': 'https://tube.tugraz.at/paella/ui/watch.html?id=f2634392-e40e-4ac7-9ddc-47764aa23d40',
        'md5': 'a23a3d5c9aaca2b84932fdba66e17145',
        'info_dict': {
            'id': 'f2634392-e40e-4ac7-9ddc-47764aa23d40',
            'ext': 'mp4',
            'title': '#6 (23.11.2017)',
            'episode': '#6 (23.11.2017)',
            'series': '[INB03001UF] Einführung in die strukturierte Programmierung',
            'creator': 'Safran C',
            'duration': 3295818,
            'series_id': 'b1192fff-2aa7-4bf0-a5cf-7b15c3bd3b34',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_data = self._download_json(
            self._API_EPISODE, video_id, query={'id': video_id, 'limit': 1}, note='Downloading episode metadata')

        episode_info = traverse_obj(episode_data, ('search-results', 'result'), default={ "id": video_id })
        return self._extract_episode(episode_info)

class TubeTuGrazSeriesIE(TubeTuGrazBaseIE):
    _VALID_URL = r'''(?x)
        https?://tube\.tugraz\.at/paella/ui/browse\.html\?series=
        (?P<id>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})
    '''
    _TESTS = []  # TODO: Add tests

    def _real_extract(self, url):
        id = self._match_id(url)
        episodes_data = self._download_json(self._API_EPISODE, id, query={'sid': id}, note='Downloading episode list')
        series_data = self._download_json(
            'https://tube.tugraz.at/series/series.json', id, fatal=False,
            note='downloading series metadata', errnote='failed to download series metadata',
            query={
                'seriesId': id,
                'count': 1,
                'sort': 'TITLE'
            })

        return self.playlist_result(
            map(self._extract_episode, episodes_data['search-results']['result']), id,
            traverse_obj(series_data, ('catalogs', 0, 'http://purl.org/dc/terms/', 'title', 0, 'value')))
