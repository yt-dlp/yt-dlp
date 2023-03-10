import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    traverse_obj,
    variadic,
)


class Echo360BaseIE(InfoExtractor):
    _INSTANCES_RE = r'''(?:
                            echo360\.ca|
                            echo360\.net\.au|
                            echo360\.org\.au|
                            echo360\.org\.uk|
                            echo360\.org|
                        )'''
    _UUID_RE = r'[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'

    def _call_api(self, host, video_id, media_id, session_token, **kwargs):
        return self._download_json(
            self._API_BASE % (host, video_id, media_id),
            video_id,
            headers={'Authorization': f'Bearer {session_token}'},
            **kwargs,
        )

    @staticmethod
    def _update_url_query(uri, query_string):
        if query_string is not None:
            return f'{uri.split("?", 1)[0]}?{query_string}'
        return uri

    @staticmethod
    def _get_query_string(uri, query_strings):
        uri_base = uri.split("?", 1)[0]
        for query_string in query_strings:
            if re.match(query_string['uriPattern'], uri_base):
                return query_string['queryString']
        return None

    def _parse_mediapackage(self, video):
        video_id = traverse_obj(video, ('playableAudioVideo', 'mediaId'))
        if video_id is None:
            raise ExtractorError('Video id was not found')
        query_strings = variadic(traverse_obj(video, ('sourceQueryStrings', 'queryStrings')) or [])
        duration = float(re.match(r'PT(\d+\.?\d+)S', traverse_obj(video, ('playableAudioVideo', 'duration')))[1])

        formats = []
        for track in variadic(traverse_obj(video, ('playableAudioVideo', 'playableMedias')) or []):
            href = track.get('uri')
            if href is None:
                continue
            href = self._update_url_query(href, self._get_query_string(href, query_strings))
            ext = determine_ext(href, None)
            is_hls = track.get('isHls')
            is_live = track.get('isLive')

            if is_hls or ext == 'm3u8':
                hls_formats = self._extract_m3u8_formats(
                    href, video_id, live=is_live, m3u8_id='hls', entry_protocol='m3u8_native', fatal=False
                )

                for hls_format in hls_formats:
                    query_string = self._get_query_string(hls_format['url'], query_strings)
                    if query_string is not None:
                        hls_format['extra_param_to_segment_url'] = query_string
                        hls_format['url'] = self._update_url_query(hls_format['url'], query_string)

                formats.extend(hls_formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('mediaName'),
            'duration': duration,
        }


class Echo360IE(Echo360BaseIE):
    _VALID_URL = rf'''(?x)
        https?://(?P<host>{Echo360BaseIE._INSTANCES_RE})
        /media/(?P<id>{Echo360BaseIE._UUID_RE})/public'''

    _API_BASE = 'https://%s/api/ui/echoplayer/public-links/%s/media/%s/player-properties'

    _TESTS = [
        {
            'url': 'https://echo360.org.uk/media/1d8392aa-a3e7-4e78-94cf-b6532c27208c/public',
            'info_dict': {
                'id': '3c7ae6e0-fa19-432d-aa21-c283b4276f2a',
                'ext': 'mp4',
                'title': '3-4 Force + moment + mechanics.mp4',
                'duration': 4731.888,
            },
            'params': {'skip_download': 'm3u8'}
        },
        {
            'url': 'https://echo360.net.au/media/f04960a9-2efc-4b63-87b5-72e629081d15/public',
            'info_dict': {
                'id': '6098a147-2d65-40f3-b9e9-a0204afe450c',
                'ext': 'mp4',
                'title': 'EXSC634_Online_Workshop_Week_4.mp4',
                'duration': 6659.72,
            },
            'params': {'skip_download': 'm3u8'}
        },
    ]

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).group('host', 'id')
        webpage = self._download_webpage(url, video_id)

        media_id = self._search_regex(rf'\\"mediaId\\":\\"({Echo360BaseIE._UUID_RE})\\"', webpage, 'media id')
        session_id = self._search_regex(rf'\\"sessionId\\":\\"({Echo360BaseIE._UUID_RE})\\"', webpage, 'session id')

        share_link_id = self._search_regex(
            rf'\\"shareLinkId\\":\\"({Echo360BaseIE._UUID_RE})\\"', webpage,
            'share link id', default=None, fatal=False)

        public_link_id = self._search_regex(
            rf'\\"publicLinkId\\":\\"({Echo360BaseIE._UUID_RE})\\"', webpage,
            'public link id', default=None, fatal=False)

        real_video_id = share_link_id or public_link_id
        if real_video_id is None:
            raise ExtractorError('Video id was not found')

        urlh = self._request_webpage(
            f'https://{host}/api/ui/sessions/{session_id}',
            video_id,
            note='Open video session',
            errnote='Unable to open video session',
        )
        session_token = urlh.headers.get('Token')
        if session_token is None:
            raise ExtractorError('Video session could not be opened')

        return self._parse_mediapackage(self._call_api(host, real_video_id, media_id, session_token)['data'])
