import re

from .common import InfoExtractor
from ..utils import determine_ext, parse_duration, traverse_obj, update_url


class Echo360IE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?P<host>echo360\.(?:ca|net\.au|org|org\.au|org\.uk))/
        media/(?P<id>[\da-fA-F]{8}-(?:[\da-fA-F]{4}-){3}[\da-fA-F]{12})/public
    '''

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

    def _call_api(self, host, video_id, media_id, session_token, **kwargs):
        return self._download_json(
            f'https://{host}/api/ui/echoplayer/public-links/{video_id}/media/{media_id}/player-properties',
            video_id, headers={'Authorization': f'Bearer {session_token}'}, **kwargs)

    def _get_query_string(self, uri, query_strings):
        uri_base = update_url(uri, query=None, fragment=None)
        for query_string in query_strings:
            try:
                if re.match(query_string['uriPattern'], uri_base):
                    return query_string['queryString']
            except re.error as re_error:
                self.report_warning(f'Error in query string pattern `{re_error.pattern}`: {re_error.msg}')
        return None

    def _parse_mediapackage(self, video):
        video_id = video['playableAudioVideo']['mediaId']
        query_strings = traverse_obj(video, ('sourceQueryStrings', 'queryStrings', ...))

        formats = []
        for track in traverse_obj(video, ('playableAudioVideo', 'playableMedias', lambda _, v: v['uri'])):
            href = update_url(track['uri'], query=self._get_query_string(track['uri'], query_strings))
            if track.get('isHls') or determine_ext(href) == 'm3u8':
                hls_formats = self._extract_m3u8_formats(
                    href, video_id, live=track.get('isLive'), m3u8_id='hls', fatal=False)

                for hls_format in hls_formats:
                    query_string = self._get_query_string(hls_format['url'], query_strings)
                    hls_format['extra_param_to_segment_url'] = query_string
                    hls_format['url'] = update_url(hls_format['url'], query=query_string)

                formats.extend(hls_formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('mediaName'),
            'duration': traverse_obj(video, ('playableAudioVideo', 'duration', {parse_duration})),
        }

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).group('host', 'id')
        webpage = self._download_webpage(url, video_id)

        player_config = self._search_json(
            r'Echo\["mediaPlayerBootstrapApp"\]\("', webpage, 'player config',
            video_id, transform_source=lambda x: x.replace(R'\"', '"'))

        urlh = self._request_webpage(
            f'https://{host}/api/ui/sessions/{player_config["sessionId"]}',
            video_id, 'Open video session', 'Unable to open video session')

        return self._parse_mediapackage(self._call_api(
            host, player_config.get('shareLinkId') or player_config['publicLinkId'],
            player_config['mediaId'], urlh.headers['Token'])['data'])
