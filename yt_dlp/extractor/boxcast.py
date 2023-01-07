import re

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    traverse_obj,
    unified_timestamp
)


class BoxCastVideoIE(InfoExtractor):
    _VALID_URL = r'''(?x)(?:
                    https?://boxcast\.tv/
                    (?:view-embed|channel|video-portal/(?:\w+/?){2})/
                    (?P<id>[\w-]+))
                '''
    _TESTS = [{
        'url': 'https://boxcast.tv/view-embed/in-the-midst-of-darkness-light-prevails-an-interdisciplinary-symposium-ozmq5eclj50ujl4bmpwx',
        'info_dict': {
            'id': 'da1eqqgkacngd5djlqld',
            'ext': 'mp4',
            'thumbnail': r're:https?://uploads\.boxcast\.com/(?:[\w+-]+/){3}.+\.png$',
            'title': 'In the Midst of Darkness Light Prevails: An Interdisciplinary Symposium',
            'release_timestamp': 1670686812,
            'release_date': '20221210',
            'uploader_id': 're8w0v8hohhvpqtbskpe',
            'uploader': 'Children\'s Health Defense',
        }
    }, {
        'url': 'https://boxcast.tv/channel/jvltpdusdnxekwvgv5gs',
        'info_dict': {
            'id': 'ezh0napskpalrimsx78m',
            'ext': 'mp4',
            'release_date': '20221121',
            'thumbnail': r're:https://uploads\.boxcast\.com/(?:[\w-]+/){3}.+\.jpg$',
            'title': 'Graveside Service | Thomas Harkelrode',
            'uploader': 'Company 119',
            'release_timestamp': 1669055702,
            'description': 'Remembering Tommy Harkelrode | Nov 21, 2022',
            'uploader_id': 'zqmbqegelwyknzleyyd3',
        }
    }, {
        'url': 'https://boxcast.tv/video-portal/vctwevwntun3o0ikq7af/rvyblnn0fxbfjx5nwxhl/otbpltj2kzkveo2qz3ad',
        'info_dict': {
            'id': 'otbpltj2kzkveo2qz3ad',
            'ext': 'mp4',
            'uploader_id': 'vctwevwntun3o0ikq7af',
            'uploader': 'Legacy Christian Church',
            'title': 'The Quest | 1: Beginner\'s Bay | Jamie Schools',
            'thumbnail': r're:https?://uploads.boxcast.com/(?:[\w-]+/){3}The_Quest2.jpg'
        }
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://childrenshealthdefense.eu/live-stream/',
        'info_dict': {
            'id': 'da1eqqgkacngd5djlqld',
            'ext': 'mp4',
            'thumbnail': r're:https?://uploads\.boxcast\.com/(?:[\w+-]+/){3}.+\.png$',
            'title': 'In the Midst of Darkness Light Prevails: An Interdisciplinary Symposium',
            'release_timestamp': 1670686812,
            'release_date': '20221210',
            'uploader_id': 're8w0v8hohhvpqtbskpe',
            'uploader': 'Children\'s Health Defense',
        }
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        mobj = re.search(
            r'<iframe[^>]+src=["\'](?P<url>https?://boxcast\.tv/view-embed/[\w-]+)',
            webpage)
        if mobj:
            yield mobj.group('url')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        webpage_json_data = self._search_json(
            r'var\s*BOXCAST_PRELOAD\s*=', webpage, 'BOXCAST_PRELOAD', display_id,
            transform_source=js_to_json, default={})

        formats, subtitles = [], {}
        broadcast_json_data = traverse_obj(webpage_json_data, ('broadcast', 'data'), default={})

        if traverse_obj(webpage_json_data, ('view', 'data', 'status'), get_all=False) == 'recorded':
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                webpage_json_data['view']['data']['playlist'], display_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if not webpage_json_data:
            # call api only if webpage_json_data didn't return expected result
            # api info at https://support.boxcast.com/en/articles/4235158-build-a-custom-viewer-experience-with-boxcast-api
            # sometimes the using rest.boxcast.com as api domain also works
            view_json_data = self._download_json(
                f'https://api.boxcast.com/broadcasts/{display_id}/view', display_id)

            fmts, subs = self._extract_m3u8_formats_and_subtitles(view_json_data['playlist'], display_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

            broadcast_json_data = self._download_json(
                f'https://api.boxcast.com/broadcasts/{display_id}', display_id)

        print(broadcast_json_data.get('preview'))
        return {
            'id': str(broadcast_json_data['id']),
            'title': broadcast_json_data.get('name'),
            'description': broadcast_json_data.get('description') or None,
            'thumbnail': broadcast_json_data.get('preview'),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': unified_timestamp(broadcast_json_data.get('streamed_at')),
            'uploader': broadcast_json_data.get('account_name'),
            'uploader_id': broadcast_json_data.get('account_id'),
        }
