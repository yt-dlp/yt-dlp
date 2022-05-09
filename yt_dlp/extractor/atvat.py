import datetime

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    jwt_encode_hs256,
    try_get,
    ExtractorError,
)


class ATVAtIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?atv\.at/tv/(?:[^/]+/){2,3}(?P<id>.*)'

    _TESTS = [{
        'url': 'https://www.atv.at/tv/bauer-sucht-frau/staffel-18/bauer-sucht-frau/bauer-sucht-frau-staffel-18-folge-3-die-hofwochen',
        'md5': '3c3b4aaca9f63e32b35e04a9c2515903',
        'info_dict': {
            'id': 'v-ce9cgn1e70n5-1',
            'ext': 'mp4',
            'title': 'Bauer sucht Frau - Staffel 18 Folge 3 - Die Hofwochen',
        }
    }, {
        'url': 'https://www.atv.at/tv/bauer-sucht-frau/staffel-18/episode-01/bauer-sucht-frau-staffel-18-vorstellungsfolge-1',
        'only_matching': True,
    }]

    # extracted from bootstrap.js function (search for e.encryption_key and use your browser's debugger)
    _ACCESS_ID = 'x_atv'
    _ENCRYPTION_KEY = 'Hohnaekeishoogh2omaeghooquooshia'

    def _extract_video_info(self, url, content, video):
        clip_id = content.get('splitId', content['id'])
        formats = []
        clip_urls = video['urls']
        for protocol, variant in clip_urls.items():
            source_url = try_get(variant, lambda x: x['clear']['url'])
            if not source_url:
                continue
            if protocol == 'dash':
                formats.extend(self._extract_mpd_formats(
                    source_url, clip_id, mpd_id=protocol, fatal=False))
            elif protocol == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    source_url, clip_id, 'mp4', 'm3u8_native',
                    m3u8_id=protocol, fatal=False))
            else:
                formats.append({
                    'url': source_url,
                    'format_id': protocol,
                })
        self._sort_formats(formats)

        return {
            'id': clip_id,
            'title': content.get('title'),
            'duration': float_or_none(content.get('duration')),
            'series': content.get('tvShowTitle'),
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._parse_json(
            self._search_regex(r'<script id="state" type="text/plain">(.*)</script>', webpage, 'json_data'),
            video_id=video_id)

        video_title = json_data['views']['default']['page']['title']
        contentResource = json_data['views']['default']['page']['contentResource']
        content_id = contentResource[0]['id']
        content_ids = [{'id': id, 'subclip_start': content['start'], 'subclip_end': content['end']}
                       for id, content in enumerate(contentResource)]

        time_of_request = datetime.datetime.now()
        not_before = time_of_request - datetime.timedelta(minutes=5)
        expire = time_of_request + datetime.timedelta(minutes=5)
        payload = {
            'content_ids': {
                content_id: content_ids,
            },
            'secure_delivery': True,
            'iat': int(time_of_request.timestamp()),
            'nbf': int(not_before.timestamp()),
            'exp': int(expire.timestamp()),
        }
        jwt_token = jwt_encode_hs256(payload, self._ENCRYPTION_KEY, headers={'kid': self._ACCESS_ID})
        videos = self._download_json(
            'https://vas-v4.p7s1video.net/4.0/getsources',
            content_id, 'Downloading videos JSON', query={
                'token': jwt_token.decode('utf-8')
            })

        video_id, videos_data = list(videos['data'].items())[0]
        error_msg = try_get(videos_data, lambda x: x['error']['title'])
        if error_msg == 'Geo check failed':
            self.raise_geo_restricted(error_msg)
        elif error_msg:
            raise ExtractorError(error_msg)
        entries = [
            self._extract_video_info(url, contentResource[video['id']], video)
            for video in videos_data]

        return {
            '_type': 'multi_video',
            'id': video_id,
            'title': video_title,
            'entries': entries,
        }
