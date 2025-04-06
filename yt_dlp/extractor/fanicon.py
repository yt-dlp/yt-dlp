import itertools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    filter_dict,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class FaniconBaseIE(InfoExtractor):
    _BASE_URL = 'https://fanicon.net'
    _API_BASE = f'{_BASE_URL}/api/fan'


class FaniconIE(FaniconBaseIE):
    _VALID_URL = r'https?://fanicon\.net/(?:fanilive|web/fancommunities)/(?P<fc_id>\d+)(?:/livearchive)?/(?P<id>[\da-f]+)(?:/(?P<slug>[\da-f]+))?'
    _TESTS = [{
        'url': 'https://fanicon.net/fanilive/4937/1224907/83fd46f739df37d',
        'info_dict': {
            'id': '1224907',
            'ext': 'mp4',
            'title': 'YAYA RECORDS CREW',
            'channel': 'YAYA RECORDS CREW',
            'channel_id': '4937',
            'display_id': '83fd46f739df37d',
            'thumbnail': r're:https://.+\.jpg',
            'timestamp': 1679835004,
            'upload_date': '20230326',
            'uploader': 'YAYA RECORDS',
            'uploader_id': '819710',
        },
    }, {
        'url': 'https://fanicon.net/web/fancommunities/5831/livearchive/1658622',
        'info_dict': {
            'id': '1658622',
            'ext': 'mp4',
            'title': 'ご相談配信❣️',
            'channel': 'ワンコインのりこ通信',
            'channel_id': '5831',
            'comment_count': int,
            'like_count': int,
            'modified_date': '20250403',
            'modified_timestamp': 1743686584,
            'thumbnail': r're:https://.+\.jpg',
            'timestamp': 1743678007,
            'upload_date': '20250403',
            'uploader': '芝崎典子',
            'uploader_id': '1147555',
        },
        'skip': 'Only available for subscribers',
    }]

    def _parse_tron(self, key, webpage, video_id):
        return self._search_json(
            rf'window\.tron\.{key}\s*=\s*', webpage, f'{key} info', video_id, default={})

    def _real_extract(self, url):
        fc_id, video_id, slug = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, video_id)

        if slug:
            live_info = self._parse_tron('live', webpage, video_id)
            file_url = live_info['url']
            is_live = not traverse_obj(live_info, ('isArchive', {bool}))
            formats = self._extract_m3u8_formats(file_url, video_id, 'mp4', live=is_live)

            metadata = {
                'display_id': slug,
                **traverse_obj(live_info, {
                    'title': ('body', {str}),
                    'timestamp': ('createdAt', {parse_iso8601}),
                }),
            }
        else:
            if not self._parse_tron('user', webpage, video_id):
                self.raise_login_required()

            cards = self._download_json(
                f'{self._API_BASE}/cards/{video_id}', video_id, query={'fanclubId': fc_id})
            if error := cards.get('error'):
                raise ExtractorError(error['message'], expected=True)

            file_url = cards['card']['media']['fileUrl']
            is_live = traverse_obj(cards, ('card', 'media', 'isOnLive', {bool}))

            if not (ext := determine_ext(file_url)):
                raise ExtractorError('Unexpected file URL')
            elif ext == 'm3u8':
                formats = self._extract_m3u8_formats(file_url, video_id, 'mp4', live=is_live)
            elif ext in {'mp3', 'mp4'}:
                formats = [{'ext': ext, 'url': file_url}]
            else:
                self.raise_no_formats(f'Unexpected file type: {ext}')

            metadata = traverse_obj(cards, ('card', {
                'title': ('body', {str.strip}),
                'comment_count': ('commentCount', {int}),
                'like_count': ('likeCount', {int}),
                'modified_timestamp': ('updatedAt', {parse_iso8601}),
                'tags': ('tags', ..., {str}),
                'timestamp': ('createdAt', {parse_iso8601}),
            }))

        return {
            'id': video_id,
            'formats': formats,
            'is_live': is_live,
            **metadata,
            **traverse_obj(self._download_json(
                f'{self._API_BASE}/fanclubs/{fc_id}', fc_id), ('fanclub', {
                    'channel': ('name', {str}),
                    'channel_id': ('id', {str_or_none}),
                    'thumbnail': ('heroImageUrl', {url_or_none}),
                    'uploader': ('owners', ..., 'name', {str}, any),
                    'uploader_id': (('ownerId', ('owners', ..., 'id')), {str_or_none}, any),
                }),
            ),
        }


class FaniconFCIE(FaniconBaseIE):
    _VALID_URL = r'https?://fanicon\.net/web/fancommunities/(?P<id>\d+)(?:/scene)?$'
    _TESTS = [{
        'url': 'https://fanicon.net/web/fancommunities/5831/scene',
        'info_dict': {
            'id': '5831',
        },
        'playlist_mincount': 14,
        'skip': 'Only available for subscribers',
    }]

    def _entries(self, fc_id):
        min_id = None
        for page in itertools.count(1):
            cards = self._download_json(
                f'{self._API_BASE}/cards', fc_id,
                f'Downloading page {page}', query=filter_dict({
                    'fanclubId': fc_id,
                    'maxId': min_id,
                }),
            )
            if not cards:
                break
            if error := cards.get('error'):
                raise ExtractorError(error['message'], expected=True)

            for media in traverse_obj(cards, ('cards', ..., 'media', {dict})):
                if all([
                    traverse_obj(media, ('fileUrl', {url_or_none})),
                    traverse_obj(media, ('isOnLive', {bool})) is not True,
                    'images' not in media,
                ]):
                    yield self.url_result(
                        f'{self._BASE_URL}/web/fancommunities/{fc_id}/livearchive/{media["cardId"]}', FaniconIE)

            if not (min_id := traverse_obj(cards, (
                'cards', ..., 'id', {int_or_none}, filter, all, {min}, {str_or_none},
            ))):
                break

    def _real_extract(self, url):
        fc_id = self._match_id(url)

        return self.playlist_result(self._entries(fc_id), fc_id)
