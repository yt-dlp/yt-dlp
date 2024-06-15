import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    make_archive_id,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class KhanAcademyBaseIE(InfoExtractor):
    _VALID_URL_TEMPL = r'https?://(?:www\.)?khanacademy\.org/(?P<id>(?:[^/]+/){%s}%s[^?#/&]+)'

    _PUBLISHED_CONTENT_VERSION = '171419ab20465d931b356f22d20527f13969bb70'

    def _parse_video(self, video):
        return {
            '_type': 'url_transparent',
            'url': video['youtubeId'],
            'id': video['youtubeId'],
            'ie_key': 'Youtube',
            **traverse_obj(video, {
                'display_id': ('id', {str_or_none}),
                'title': ('translatedTitle', {str}),
                'thumbnail': ('thumbnailUrls', ..., 'url', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'description': ('description', {str}),
            }, get_all=False),
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        content = self._download_json(
            'https://www.khanacademy.org/api/internal/graphql/ContentForPath', display_id,
            query={
                'fastly_cacheable': 'persist_until_publish',
                'pcv': self._PUBLISHED_CONTENT_VERSION,
                'hash': '1242644265',
                'variables': json.dumps({
                    'path': display_id,
                    'countryCode': 'US',
                    'kaLocale': 'en',
                    'clientPublishedContentVersion': self._PUBLISHED_CONTENT_VERSION,
                }),
                'lang': 'en',
            })['data']['contentRoute']['listedPathData']
        return self._parse_component_props(content, display_id)


class KhanAcademyIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy'
    _VALID_URL = KhanAcademyBaseIE._VALID_URL_TEMPL % ('4', 'v/')
    _TEST = {
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography/crypt/v/one-time-pad',
        'md5': '1d5c2e70fa6aa29c38eca419f12515ce',
        'info_dict': {
            'id': 'FlIG3TvQCBQ',
            'ext': 'mp4',
            'title': 'The one-time pad',
            'description': 'The perfect cipher',
            'display_id': '716378217',
            'duration': 176,
            'uploader': 'Khan Academy',
            'uploader_id': '@khanacademy',
            'uploader_url': 'https://www.youtube.com/@khanacademy',
            'upload_date': '20120411',
            'timestamp': 1334170113,
            'license': 'cc-by-nc-sa',
            'live_status': 'not_live',
            'channel': 'Khan Academy',
            'channel_id': 'UC4a-Gbdw7vOaccHmFo40b9g',
            'channel_url': 'https://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g',
            'channel_is_verified': True,
            'playable_in_embed': True,
            'categories': ['Education'],
            'creators': ['Brit Cruise'],
            'tags': [],
            'age_limit': 0,
            'availability': 'public',
            'comment_count': int,
            'channel_follower_count': int,
            'thumbnail': str,
            'view_count': int,
            'like_count': int,
            'heatmap': list,
        },
        'add_ie': ['Youtube'],
    }

    def _parse_component_props(self, component_props, display_id):
        video = component_props['content']
        return {
            **self._parse_video(video),
            **traverse_obj(video, {
                'creators': ('authorNames', ..., {str}),
                'timestamp': ('dateAdded', {parse_iso8601}),
                'license': ('kaUserLicense', {str}),
            }),
        }


class KhanAcademyUnitIE(KhanAcademyBaseIE):
    IE_NAME = 'khanacademy:unit'
    _VALID_URL = (KhanAcademyBaseIE._VALID_URL_TEMPL % ('1,2', '')) + '/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'https://www.khanacademy.org/computing/computer-science/cryptography',
        'info_dict': {
            'id': 'x48c910b6',
            'title': 'Cryptography',
            'description': 'How have humans protected their secret messages through history? What has changed today?',
            'display_id': 'computing/computer-science/cryptography',
            '_old_archive_ids': ['khanacademyunit cryptography'],
        },
        'playlist_mincount': 31,
    }, {
        'url': 'https://www.khanacademy.org/computing/computer-science',
        'info_dict': {
            'id': 'x301707a0',
            'title': 'Computer science theory',
            'description': 'md5:4b472a4646e6cf6ec4ccb52c4062f8ba',
            'display_id': 'computing/computer-science',
            '_old_archive_ids': ['khanacademyunit computer-science'],
        },
        'playlist_mincount': 50,
    }]

    def _parse_component_props(self, component_props, display_id):
        course = component_props['course']
        selected_unit = traverse_obj(course, (
            'unitChildren', lambda _, v: v['relativeUrl'] == f'/{display_id}', any)) or course

        def build_entry(entry):
            return self.url_result(urljoin(
                'https://www.khanacademy.org', entry['canonicalUrl']),
                KhanAcademyIE, title=entry.get('translatedTitle'))

        entries = traverse_obj(selected_unit, (
            (('unitChildren', ...), None), 'allOrderedChildren', ..., 'curatedChildren',
            lambda _, v: v['contentKind'] == 'Video' and v['canonicalUrl'], {build_entry}))

        return self.playlist_result(
            entries,
            display_id=display_id,
            **traverse_obj(selected_unit, {
                'id': ('id', {str}),
                'title': ('translatedTitle', {str}),
                'description': ('translatedDescription', {str}),
                '_old_archive_ids': ('slug', {str}, {lambda x: [make_archive_id(self, x)] if x else None}),
            }))
