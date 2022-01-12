# coding: utf-8
import json

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_codecs,
    traverse_obj,
    urljoin,
)


class StreamCZIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:stream|televizeseznam)\.cz/[^?#]+/(?P<display_id>[^?#]+)-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.televizeseznam.cz/video/lajna/buh-57953890',
        'md5': '40c41ade1464a390a0b447e333df4239',
        'info_dict': {
            'id': '57953890',
            'ext': 'mp4',
            'title': 'Bůh',
            'display_id': 'buh',
            'description': 'md5:8f5f09b9b7bc67df910486cdd88f7165',
        }
    }, {
        'url': 'https://www.stream.cz/tajemno/znicehonic-jim-skrz-strechu-prolitnul-zahadny-predmet-badatele-vse-objasnili-64147267',
        'md5': '3ee4d0be040e8f4a543e67e509d55e3f',
        'info_dict': {
            'id': '64147267',
            'ext': 'mp4',
            'title': 'Zničehonic jim skrz střechu prolítnul záhadný předmět. Badatelé vše objasnili',
            'display_id': 'znicehonic-jim-skrz-strechu-prolitnul-zahadny-predmet-badatele-vse-objasnili',
            'description': 'md5:1dcb5e010eb697dedc5942f76c5b3744',
        }
    }]

    def _extract_formats(self, spl_url, video):
        for ext, pref, streams in (
                ('ts', -1, traverse_obj(video, ('http_stream', 'qualities'))),
                ('mp4', 1, video.get('mp4'))):
            for format_id, stream in streams.items():
                if not stream.get('url'):
                    continue
                yield {
                    'format_id': f'{format_id}-{ext}',
                    'ext': ext,
                    'source_preference': pref,
                    'url': urljoin(spl_url, stream['url']),
                    'tbr': float_or_none(stream.get('bandwidth'), scale=1000),
                    'duration': float_or_none(stream.get('duration'), scale=1000),
                    'width': traverse_obj(stream, ('resolution', 0)),
                    'height': traverse_obj(stream, ('resolution', 1)) or int_or_none(format_id.replace('p', '')),
                    **parse_codecs(stream.get('codec')),
                }

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()

        data = self._download_json(
            'https://www.televizeseznam.cz/api/graphql', video_id, 'Downloading GraphQL result',
            data=json.dumps({
                'variables': {'urlName': video_id},
                'query': '''
                    query LoadEpisode($urlName : String){ episode(urlName: $urlName){ ...VideoDetailFragmentOnEpisode } }
                    fragment VideoDetailFragmentOnEpisode on Episode {
                        id
                        spl
                        urlName
                        name
                        perex
                        duration
                        views
                    }'''
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )['data']['episode']

        spl_url = data['spl'] + 'spl2,3'
        metadata = self._download_json(spl_url, video_id, 'Downloading playlist')
        if 'Location' in metadata and 'data' not in metadata:
            spl_url = metadata['Location']
            metadata = self._download_json(spl_url, video_id, 'Downloading redirected playlist')
        video = metadata['data']

        subtitles = {}
        for subs in video.get('subtitles', {}).values():
            if not subs.get('language'):
                continue
            for ext, sub_url in subs.get('urls').items():
                subtitles.setdefault(subs['language'], []).append({
                    'ext': ext,
                    'url': urljoin(spl_url, sub_url)
                })

        formats = list(self._extract_formats(spl_url, video))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': data.get('name'),
            'description': data.get('perex'),
            'duration': float_or_none(data.get('duration')),
            'view_count': int_or_none(data.get('views')),
            'formats': formats,
            'subtitles': subtitles,
        }
