# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    parse_iso8601,
    parse_resolution,
    int_or_none,
    try_get,
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

    def _call_api(self, host, video_id, note=None, errnote=None, fatal=True):
        return self._download_json(self._API_BASE % (host, video_id), video_id, note=note, errnote=errnote, fatal=fatal)

    def _parse_mediapackage(self, video):
        tracks = try_get(video, lambda x: x['media']['track'])

        video_id = video.get('id')

        formats = []
        for track in tracks:
            href = track['url']
            ext = determine_ext(href, None)
            track_obj = {'url': href}

            transport = track.get('transport')

            if transport == 'DASH' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats_and_subtitles(href, video_id, mpd_id='dash', fatal=False))
            elif transport == 'HLS' or ext == 'm3u8':
                formats.extend(
                    self._extract_m3u8_formats_and_subtitles(href, video_id, m3u8_id='hls', entry_protocol='m3u8_native', fatal=False)
                )
            elif transport == 'HDS' or ext == 'f4m':
                formats.extend(self._extract_f4m_formats(href, video_id, f4m_id='hds', fatal=False))
            elif transport == 'SMOOTH':
                formats.extend(self._extract_ism_formats(href, video_id, ism_id='smooth', fatal=False))
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(href, video_id, fatal=False))
            else:
                if transport is not None:
                    track_obj.update({'format_note': track.get('transport')})
                    if transport == 'RTMP':
                        m_obj = re.search(r'^(?:rtmp://[^/]+/(?P<app>[^/]+))/(?P<playpath>.+)$', href)
                        if not m_obj:
                            continue
                        track_obj.update(
                            {
                                'app': m_obj.group('app'),
                                'play_path': m_obj.group('playpath'),
                                'rtmp_live': True,
                                'preference': -2,
                            }
                        )
                        extention = m_obj.group('playpath').split(':')
                        if len(extention) > 1:
                            track_obj.update({'ext': extention[0]})

                audio_info = track.get('audio')
                if audio_info is not None:
                    if 'bitrate' in audio_info:
                        track_obj.update({'abr': int_or_none(audio_info.get('bitrate'), 1000)})
                    if 'samplingrate' in audio_info:
                        track_obj.update({'asr': int_or_none(audio_info.get('samplingrate'))})
                    audio_encoder = audio_info.get('encoder', {})
                    if 'type' in audio_encoder:
                        track_obj.update({'acodec': audio_encoder.get('type')})

                video_info = track.get('video')
                if video_info is not None:
                    if 'resolution' in video_info:
                        track_obj.update({'resolution': video_info.get('resolution')})
                        resolution = parse_resolution(video_info.get('resolution'))
                        track_obj.update(resolution)
                    if 'framerate' in video_info:
                        track_obj.update({'fps': int_or_none(video_info.get('framerate'))})
                    if 'bitrate' in video_info:
                        track_obj.update({'vbr': int_or_none(video_info.get('bitrate'), 1000)})
                    video_encoder = video_info.get('encoder', {})
                    if 'type' in video_encoder:
                        track_obj.update({'vcodec': video_encoder.get('type')})

                formats.append(track_obj)

        self._sort_formats(formats)

        result_obj = {'formats': formats}

        result_obj.update({'id': video_id})

        title = video.get('title')
        if title is not None:
            result_obj.update({'title': title})

        series = video.get('seriestitle')
        if series is not None:
            result_obj.update({'series': series})

        season_id = video.get('series')
        if season_id is not None:
            result_obj.update({'season_id': season_id})

        creator = video.get('creators', {}).get('creator')
        if creator is not None:
            result_obj.update({'creator': creator})

        timestamp = parse_iso8601(video.get('start'))
        if timestamp is not None:
            result_obj.update({'timestamp': timestamp})

        attachments = video.get('attachments', {}).get('attachment', [])
        if len(attachments) > 0:
            thumbnail = attachments[0].get('url')
            result_obj.update({'thumbnail': thumbnail})

        return result_obj


class OpencastIE(OpencastBaseIE):
    _VALID_URL = r'''(?x)
                    https?://(?P<host>%s)/paella/ui/watch.html\?.*?
                    id=(?P<id>%s)
                    ''' % (
        OpencastBaseIE._INSTANCES_RE,
        OpencastBaseIE._UUID_RE,
    )

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
            },
        }
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        host = mobj.group('host')
        video_id = mobj.group('id')

        video = self._call_api(host, video_id, note='Downloading video JSON')['search-results']['result']['mediapackage']

        return self._parse_mediapackage(video)


class OpencastPlaylistIE(OpencastBaseIE):
    _VALID_URL = r'''(?x)
                            https?://(?P<host>%s)/engage/ui/index.html\?.*?
                            epFrom=(?P<id>%s)
                    ''' % (
        OpencastBaseIE._INSTANCES_RE,
        OpencastBaseIE._UUID_RE,
    )

    _API_BASE = 'https://%s/search/episode.json?sid=%s'

    _TESTS = [
        {
            'url': 'https://oc-video1.ruhr-uni-bochum.de/engage/ui/index.html?epFrom=cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
            'info_dict': {
                'id': 'cf68a4a1-36b1-4a53-a6ba-61af5705a0d0',
                'title': 'Kryptographie - WiSe 15/16',
            },
            'playlist_mincount': 28,
        },
        {
            'url': 'https://oc-video.ruhr-uni-bochum.de/engage/ui/index.html?e=1&p=1&epFrom=b1a54262-3684-403f-9731-8e77c3766f9a',
            'info_dict': {
                'id': 'b1a54262-3684-403f-9731-8e77c3766f9a',
                'title': 'inSTUDIES-Social movements and prefigurative politics in a global perspective',
            },
            'playlist_mincount': 8,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host')
        video_id = mobj.group('id')

        result_list = self._call_api(host, video_id, note='Downloading video JSON')['search-results']['result']

        if isinstance(result_list, dict):
            result_list = [result_list]

        entries = [
            self._parse_mediapackage(episode['mediapackage'])
            for episode in result_list
            if episode.get('mediapackage')]

        return self.playlist_result(entries, playlist_id=video_id, playlist_title=try_get(entries, lambda x: x[0]['series']))
