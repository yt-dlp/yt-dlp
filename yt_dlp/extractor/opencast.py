import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    variadic,
)


class OpencastBaseIE(InfoExtractor):
    _INSTANCES_RE = r'''(?:
                            opencast\.informatik\.kit\.edu|
                            electures\.uni-muenster\.de|
                            oc-presentation\.ltcc\.tuwien\.ac\.at|
                            medien\.ph-noe\.ac\.at|
                            oc-video\.ruhr-uni-bochum\.de|
                            oc-video1\.ruhr-uni-bochum\.de|
                            opencast\.informatik\.uni-goettingen\.de|
                            heicast\.uni-heidelberg\.de|
                            opencast\.hawk\.de:8080|
                            opencast\.hs-osnabrueck\.de|
                            video[0-9]+\.virtuos\.uni-osnabrueck\.de|
                            opencast\.uni-koeln\.de|
                            media\.opencast\.hochschule-rhein-waal\.de|
                            matterhorn\.dce\.harvard\.edu|
                            hs-harz\.opencast\.uni-halle\.de|
                            videocampus\.urz\.uni-leipzig\.de|
                            media\.uct\.ac\.za|
                            vid\.igb\.illinois\.edu|
                            cursosabertos\.c3sl\.ufpr\.br|
                            mcmedia\.missioncollege\.org|
                            clases\.odon\.edu\.uy
                        )'''
    _UUID_RE = r'[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'

    def _call_api(self, host, video_id, **kwargs):
        return self._download_json(self._API_BASE % (host, video_id), video_id, **kwargs)

    def _parse_mediapackage(self, video):
        video_id = video.get('id')
        if video_id is None:
            raise ExtractorError('Video id was not found')

        formats = []
        for track in variadic(traverse_obj(video, ('media', 'track')) or []):
            href = track.get('url')
            if href is None:
                continue
            ext = determine_ext(href, None)

            transport = track.get('transport')

            if transport == 'DASH' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(href, video_id, mpd_id='dash', fatal=False))
            elif transport == 'HLS' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    href, video_id, m3u8_id='hls', entry_protocol='m3u8_native', fatal=False))
            elif transport == 'HDS' or ext == 'f4m':
                formats.extend(self._extract_f4m_formats(href, video_id, f4m_id='hds', fatal=False))
            elif transport == 'SMOOTH':
                formats.extend(self._extract_ism_formats(href, video_id, ism_id='smooth', fatal=False))
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(href, video_id, fatal=False))
            else:
                track_obj = {
                    'url': href,
                    'ext': ext,
                    'format_note': track.get('transport'),
                    'resolution': traverse_obj(track, ('video', 'resolution')),
                    'fps': int_or_none(traverse_obj(track, ('video', 'framerate'))),
                    'vbr': int_or_none(traverse_obj(track, ('video', 'bitrate')), scale=1000),
                    'vcodec': traverse_obj(track, ('video', 'encoder', 'type')) if track.get('video') else 'none',
                    'abr': int_or_none(traverse_obj(track, ('audio', 'bitrate')), scale=1000),
                    'asr': int_or_none(traverse_obj(track, ('audio', 'samplingrate'))),
                    'acodec': traverse_obj(track, ('audio', 'encoder', 'type')) if track.get('audio') else 'none',
                }

                if transport == 'RTMP':
                    m_obj = re.search(r'(?:rtmp://[^/]+/(?P<app>[^/]+))/(?P<ext>.+):(?P<playpath>.+)', href)
                    if not m_obj:
                        continue
                    track_obj.update({
                        'app': m_obj.group('app'),
                        'ext': m_obj.group('ext'),
                        'play_path': m_obj.group('ext') + ':' + m_obj.group('playpath'),
                        'rtmp_live': True,
                        'preference': -2,
                    })
                formats.append(track_obj)

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('title'),
            'series': video.get('seriestitle'),
            'season_id': video.get('series'),
            'creator': traverse_obj(video, ('creators', 'creator')),
            'timestamp': parse_iso8601(video.get('start')),
            'thumbnail': traverse_obj(video, ('attachments', 'attachment', ..., 'url'), get_all=False),
        }


class OpencastIE(OpencastBaseIE):
    _VALID_URL = rf'''(?x)
        https?://(?P<host>{OpencastBaseIE._INSTANCES_RE})/paella/ui/watch\.html\?
        (?:[^#]+&)?id=(?P<id>{OpencastBaseIE._UUID_RE})'''

    _API_BASE = 'https://%s/search/episode.json?id=%s'

    _TESTS = [
        {
            'url': 'https://oc-video1.ruhr-uni-bochum.de/paella/ui/watch.html?id=ed063cd5-72c8-46b5-a60a-569243edcea8',
            'md5': '554c8e99a90f7be7e874619fcf2a3bc9',
            'info_dict': {
                'id': 'ed063cd5-72c8-46b5-a60a-569243edcea8',
                'ext': 'mp4',
                'title': '11 - Kryptographie - 24.11.2015',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1606208400,
                'upload_date': '20201124',
                'season_id': 'cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
                'series': 'Kryptographie - WiSe 15/16',
                'creator': 'Alexander May',
            },
        },
    ]

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).group('host', 'id')
        return self._parse_mediapackage(
            self._call_api(host, video_id)['search-results']['result']['mediapackage'])


class OpencastPlaylistIE(OpencastBaseIE):
    _VALID_URL = rf'''(?x)
        https?://(?P<host>{OpencastBaseIE._INSTANCES_RE})(?:
            /engage/ui/index\.html\?(?:[^#]+&)?epFrom=|
            /ltitools/index\.html\?(?:[^#]+&)?series=
        )(?P<id>{OpencastBaseIE._UUID_RE})'''

    _API_BASE = 'https://%s/search/episode.json?sid=%s'

    _TESTS = [
        {
            'url': 'https://oc-video1.ruhr-uni-bochum.de/engage/ui/index.html?epFrom=cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
            'info_dict': {
                'id': 'cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
                'title': 'Kryptographie - WiSe 15/16',
            },
            'playlist_mincount': 29,
        },
        {
            'url': 'https://oc-video1.ruhr-uni-bochum.de/ltitools/index.html?subtool=series&series=cf68a4a1-36b1-4a53-a6ba-61af5705a0d0&lng=de',
            'info_dict': {
                'id': 'cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
                'title': 'Kryptographie - WiSe 15/16',
            },
            'playlist_mincount': 29,
        },
        {
            'url': 'https://electures.uni-muenster.de/engage/ui/index.html?e=1&p=1&epFrom=39391d10-a711-4d23-b21d-afd2ed7d758c',
            'info_dict': {
                'id': '39391d10-a711-4d23-b21d-afd2ed7d758c',
                'title': '021670 Theologische Themen bei Hans Blumenberg WiSe 2017/18',
            },
            'playlist_mincount': 13,
        },
    ]

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).group('host', 'id')

        entries = [
            self._parse_mediapackage(episode['mediapackage'])
            for episode in variadic(self._call_api(host, video_id)['search-results']['result'])
            if episode.get('mediapackage')
        ]

        return self.playlist_result(entries, video_id, traverse_obj(entries, (0, 'series')))
