from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj, unified_timestamp


class BoxCastVideoIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://boxcast\.tv/(?:
            view-embed/|
            channel/\w+\?(?:[^#]+&)?b=|
            video-portal/(?:\w+/){2}
        )(?P<id>[\w-]+)'''
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>https?://boxcast\.tv/view-embed/[\w-]+)']
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
        },
    }, {
        'url': 'https://boxcast.tv/video-portal/vctwevwntun3o0ikq7af/rvyblnn0fxbfjx5nwxhl/otbpltj2kzkveo2qz3ad',
        'info_dict': {
            'id': 'otbpltj2kzkveo2qz3ad',
            'ext': 'mp4',
            'uploader_id': 'vctwevwntun3o0ikq7af',
            'uploader': 'Legacy Christian Church',
            'title': 'The Quest | 1: Beginner\'s Bay | Jamie Schools',
            'thumbnail': r're:https?://uploads.boxcast.com/(?:[\w-]+/){3}.+\.jpg',
        },
    }, {
        'url': 'https://boxcast.tv/channel/z03fqwaeaby5lnaawox2?b=ssihlw5gvfij2by8tkev',
        'info_dict': {
            'id': 'ssihlw5gvfij2by8tkev',
            'ext': 'mp4',
            'thumbnail': r're:https?://uploads.boxcast.com/(?:[\w-]+/){3}.+\.jpg$',
            'release_date': '20230101',
            'uploader_id': 'ds25vaazhlu4ygcvffid',
            'release_timestamp': 1672543201,
            'uploader': 'Lighthouse Ministries International  - Beltsville, Maryland',
            'description': 'md5:ac23e3d01b0b0be592e8f7fe0ec3a340',
            'title': 'New Year\'s Eve CROSSOVER Service at LHMI | December 31, 2022',
        },
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
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        webpage_json_data = self._search_json(
            r'var\s*BOXCAST_PRELOAD\s*=', webpage, 'broadcast data', display_id,
            transform_source=js_to_json, default={})

        # Ref: https://support.boxcast.com/en/articles/4235158-build-a-custom-viewer-experience-with-boxcast-api
        broadcast_json_data = (
            traverse_obj(webpage_json_data, ('broadcast', 'data'))
            or self._download_json(f'https://api.boxcast.com/broadcasts/{display_id}', display_id))
        view_json_data = (
            traverse_obj(webpage_json_data, ('view', 'data'))
            or self._download_json(f'https://api.boxcast.com/broadcasts/{display_id}/view',
                                   display_id, fatal=False) or {})

        formats, subtitles = [], {}
        if view_json_data.get('status') == 'recorded':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                view_json_data['playlist'], display_id)

        return {
            'id': str(broadcast_json_data['id']),
            'title': (broadcast_json_data.get('name')
                      or self._html_search_meta(['og:title', 'twitter:title'], webpage)),
            'description': (broadcast_json_data.get('description')
                            or self._html_search_meta(['og:description', 'twitter:description'], webpage)
                            or None),
            'thumbnail': (broadcast_json_data.get('preview')
                          or self._html_search_meta(['og:image', 'twitter:image'], webpage)),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': unified_timestamp(broadcast_json_data.get('streamed_at')),
            'uploader': broadcast_json_data.get('account_name'),
            'uploader_id': broadcast_json_data.get('account_id'),
        }
