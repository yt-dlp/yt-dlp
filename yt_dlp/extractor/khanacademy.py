import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    try_get,
)


class KhanAcademyBaseIE(InfoExtractor):
    _VALID_URL_TEMPL = r'https?://(?:www\.)?khanacademy\.org/(?P<id>(?:[^/]+/){%s}%s[^?#/&]+)'

    def _parse_video(self, video):
        return {
            '_type': 'url_transparent',
            'url': video['youtubeId'],
            'id': video.get('slug'),
            'title': video.get('title'),
            'thumbnail': video.get('imageUrl') or video.get('thumbnailUrl'),
            'duration': int_or_none(video.get('duration')),
            'description': video.get('description'),
            'ie_key': 'Youtube',
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        content = self._download_json(
            'https://www.khanacademy.org/api/internal/graphql/FetchContentData',
            display_id, query={
                'fastly_cacheable': 'persist_until_publish',
                'hash': '4134764944',
                'lang': 'en',
                'variables': json.dumps({
                    'path': display_id,
                    'queryParams': 'lang=en',
                    'isModal': False,
                    'followRedirects': True,
                    'countryCode': 'US',
                }),
            })['data']['contentJson']
        return self._parse_component_props(self._parse_json(content, display_id)['componentProps'])


class KhanAcademyIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy'
    _VALID_URL = KhanAcademyBaseIE._VALID_URL_TEMPL % ('4', 'v/')
    _TEST = {
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography/crypt/v/one-time-pad',
        'md5': '9c84b7b06f9ebb80d22a5c8dedefb9a0',
        'info_dict': {
            'id': 'FlIG3TvQCBQ',
            'ext': 'mp4',
            'title': 'The one-time pad',
            'description': 'The perfect cipher',
            'duration': 176,
            'uploader': 'Brit Cruise',
            'uploader_id': 'khanacademy',
            'upload_date': '20120411',
            'timestamp': 1334170113,
            'license': 'cc-by-nc-sa',
        },
        'add_ie': ['Youtube'],
    }

    def _parse_component_props(self, component_props):
        video = component_props['tutorialPageData']['contentModel']
        info = self._parse_video(video)
        author_names = video.get('authorNames')
        info.update({
            'uploader': ', '.join(author_names) if author_names else None,
            'timestamp': parse_iso8601(video.get('dateAdded')),
            'license': video.get('kaUserLicense'),
        })
        return info


class KhanAcademyUnitIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy:unit'
    _VALID_URL = (KhanAcademyBaseIE._VALID_URL_TEMPL % ('2', '')) + '/?(?:[?#&]|$)'
    _TEST = {
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography',
        'info_dict': {
            'id': 'cryptography',
            'title': 'Cryptography',
            'description': 'How have humans protected their secret messages through history? What has changed today?',
        },
        'playlist_mincount': 31,
    }

    def _parse_component_props(self, component_props):
        curation = component_props['curation']

        entries = []
        tutorials = try_get(curation, lambda x: x['tabs'][0]['modules'][0]['tutorials'], list) or []
        for tutorial_number, tutorial in enumerate(tutorials, 1):
            chapter_info = {
                'chapter': tutorial.get('title'),
                'chapter_number': tutorial_number,
                'chapter_id': tutorial.get('id'),
            }
            for content_item in (tutorial.get('contentItems') or []):
                if content_item.get('kind') == 'Video':
                    info = self._parse_video(content_item)
                    info.update(chapter_info)
                    entries.append(info)

        return self.playlist_result(
            entries, curation.get('unit'), curation.get('title'),
            curation.get('description'))
