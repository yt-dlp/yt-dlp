# coding: utf-8
from __future__ import unicode_literals

import itertools
from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    urljoin,
    traverse_obj,
    int_or_none,
    mimetype2ext,
    clean_html,
    url_or_none,
    unified_timestamp,
    str_or_none,
)


class PRXBaseIE(InfoExtractor):
    PRX_BASE_URL_RE = r'https?://(?:(?:beta|listen)\.)?prx.org/%s'

    def _call_api(self, item_id, path, query=None, fatal=True, note='Downloading CMS API JSON'):
        return self._download_json(
            urljoin('https://cms.prx.org/api/v1/', path), item_id, query=query, fatal=fatal, note=note)

    @staticmethod
    def _get_prx_embed_response(response, section):
        return traverse_obj(response, ('_embedded', f'prx:{section}'))

    @staticmethod
    def _extract_file_link(response):
        return url_or_none(traverse_obj(
            response, ('_links', 'enclosure', 'href'), expected_type=str))

    @classmethod
    def _extract_image(cls, image_response):
        if not isinstance(image_response, dict):
            return
        return {
            'id': str_or_none(image_response.get('id')),
            'filesize': image_response.get('size'),
            'width': image_response.get('width'),
            'height': image_response.get('height'),
            'url': cls._extract_file_link(image_response)
        }

    @classmethod
    def _extract_base_info(cls, response):
        if not isinstance(response, dict):
            return
        item_id = str_or_none(response.get('id'))
        if not item_id:
            return
        thumbnail_dict = cls._extract_image(cls._get_prx_embed_response(response, 'image'))
        description = (
            clean_html(response.get('description'))
            or response.get('shortDescription'))
        return {
            'id': item_id,
            'title': response.get('title') or item_id,
            'thumbnails': [thumbnail_dict] if thumbnail_dict else None,
            'description': description,
            'release_timestamp': unified_timestamp(response.get('releasedAt')),
            'timestamp': unified_timestamp(response.get('createdAt')),
            'modified_timestamp': unified_timestamp(response.get('updatedAt')),
            'duration': int_or_none(response.get('duration')),
            'tags': response.get('tags'),
            'episode_number': int_or_none(response.get('episodeIdentifier')),
            'season_number': int_or_none(response.get('seasonIdentifier'))
        }

    @classmethod
    def _extract_series_info(cls, series_response):
        base_info = cls._extract_base_info(series_response)
        if not base_info:
            return
        account_info = cls._extract_account_info(
            cls._get_prx_embed_response(series_response, 'account')) or {}
        return {
            **base_info,
            'channel_id': account_info.get('channel_id'),
            'channel_url': account_info.get('channel_url'),
            'channel': account_info.get('channel'),
            'series': base_info.get('title'),
            'series_id': base_info.get('id'),
        }

    @classmethod
    def _extract_account_info(cls, account_response):
        base_info = cls._extract_base_info(account_response)
        if not base_info:
            return
        name = account_response.get('name')
        return {
            **base_info,
            'title': name,
            'channel_id': base_info.get('id'),
            'channel_url': 'https://beta.prx.org/accounts/%s' % base_info.get('id'),
            'channel': name,
        }

    @classmethod
    def _extract_story_info(cls, story_response):
        base_info = cls._extract_base_info(story_response)
        if not base_info:
            return
        series = cls._extract_series_info(
            cls._get_prx_embed_response(story_response, 'series')) or {}
        account = cls._extract_account_info(
            cls._get_prx_embed_response(story_response, 'account')) or {}
        return {
            **base_info,
            'series': series.get('series'),
            'series_id': series.get('series_id'),
            'channel_id': account.get('channel_id'),
            'channel_url': account.get('channel_url'),
            'channel': account.get('channel')
        }

    def _entries(self, item_id, endpoint, entry_func, query=None):
        """
        Extract entries from paginated list API
        @param entry_func: Function to generate entry from response item
        """
        total = 0
        for page in itertools.count(1):
            response = self._call_api(f'{item_id}: page {page}', endpoint, query={
                **(query or {}),
                'page': page,
                'per': 100
            })
            items = self._get_prx_embed_response(response, 'items')
            if not response or not items:
                break

            yield from filter(None, map(entry_func, items))

            total += response['count']
            if total >= response['total']:
                break

    def _story_playlist_entry(self, response):
        story = self._extract_story_info(response)
        if not story:
            return
        story.update({
            '_type': 'url',
            'url': 'https://beta.prx.org/stories/%s' % story['id'],
            'ie_key': PRXStoryIE.ie_key()
        })
        return story

    def _series_playlist_entry(self, response):
        series = self._extract_series_info(response)
        if not series:
            return
        series.update({
            '_type': 'url',
            'url': 'https://beta.prx.org/series/%s' % series['id'],
            'ie_key': PRXSeriesIE.ie_key()
        })
        return series


class PRXStoryIE(PRXBaseIE):
    _VALID_URL = PRXBaseIE.PRX_BASE_URL_RE % r'stories/(?P<id>\d+)'

    _TESTS = [
        {
            # Story with season and episode details
            'url': 'https://beta.prx.org/stories/399200',
            'info_dict': {
                'id': '399200',
                'title': 'Fly Me To The Moon',
                'description': 'md5:43230168390b95d3322048d8a56bf2bb',
                'release_timestamp': 1640250000,
                'timestamp': 1640208972,
                'modified_timestamp': 1641318202,
                'duration': 1004,
                'tags': 'count:7',
                'episode_number': 8,
                'season_number': 5,
                'series': 'AirSpace',
                'series_id': '38057',
                'channel_id': '220986',
                'channel_url': 'https://beta.prx.org/accounts/220986',
                'channel': 'Air and Space Museum',
            },
            'playlist': [{
                'info_dict': {
                    'id': '399200_part1',
                    'title': 'Fly Me To The Moon',
                    'description': 'md5:43230168390b95d3322048d8a56bf2bb',
                    'release_timestamp': 1640250000,
                    'timestamp': 1640208972,
                    'modified_timestamp': 1641318202,
                    'duration': 530,
                    'tags': 'count:7',
                    'episode_number': 8,
                    'season_number': 5,
                    'series': 'AirSpace',
                    'series_id': '38057',
                    'channel_id': '220986',
                    'channel_url': 'https://beta.prx.org/accounts/220986',
                    'channel': 'Air and Space Museum',
                    'ext': 'mp3',
                    'upload_date': '20211222',
                    'episode': 'Episode 8',
                    'release_date': '20211223',
                    'season': 'Season 5',
                    'modified_date': '20220104'
                }
            }, {
                'info_dict': {
                    'id': '399200_part2',
                    'title': 'Fly Me To The Moon',
                    'description': 'md5:43230168390b95d3322048d8a56bf2bb',
                    'release_timestamp': 1640250000,
                    'timestamp': 1640208972,
                    'modified_timestamp': 1641318202,
                    'duration': 474,
                    'tags': 'count:7',
                    'episode_number': 8,
                    'season_number': 5,
                    'series': 'AirSpace',
                    'series_id': '38057',
                    'channel_id': '220986',
                    'channel_url': 'https://beta.prx.org/accounts/220986',
                    'channel': 'Air and Space Museum',
                    'ext': 'mp3',
                    'upload_date': '20211222',
                    'episode': 'Episode 8',
                    'release_date': '20211223',
                    'season': 'Season 5',
                    'modified_date': '20220104'
                }
            }

            ]
        }, {
            # Story with only split audio
            'url': 'https://beta.prx.org/stories/326414',
            'info_dict': {
                'id': '326414',
                'title': 'Massachusetts v EPA',
                'description': 'md5:744fffba08f19f4deab69fa8d49d5816',
                'timestamp': 1592509124,
                'modified_timestamp': 1592510457,
                'duration': 3088,
                'tags': 'count:0',
                'series': 'Outside/In',
                'series_id': '36252',
                'channel_id': '206',
                'channel_url': 'https://beta.prx.org/accounts/206',
                'channel': 'New Hampshire Public Radio',
            },
            'playlist_count': 4
        }, {
            # Story with single combined audio
            'url': 'https://beta.prx.org/stories/400404',
            'info_dict': {
                'id': '400404',
                'title': 'Cafe Chill (Episode 2022-01)',
                'thumbnails': 'count:1',
                'description': 'md5:9f1b5a3cbd64fb159d08c3baa31f1539',
                'timestamp': 1641233952,
                'modified_timestamp': 1641234248,
                'duration': 3540,
                'series': 'Café Chill',
                'series_id': '37762',
                'channel_id': '5767',
                'channel_url': 'https://beta.prx.org/accounts/5767',
                'channel': 'C89.5 - KNHC Seattle',
                'ext': 'mp3',
                'tags': 'count:0',
                'thumbnail': r're:https?://cms\.prx\.org/pub/\w+/0/web/story_image/767965/medium/Aurora_Over_Trees\.jpg',
                'upload_date': '20220103',
                'modified_date': '20220103'
            }
        }, {
            'url': 'https://listen.prx.org/stories/399200',
            'only_matching': True
        }
    ]

    def _extract_audio_pieces(self, audio_response):
        return [{
            'format_id': str_or_none(piece_response.get('id')),
            'format_note': str_or_none(piece_response.get('label')),
            'filesize': int_or_none(piece_response.get('size')),
            'duration': int_or_none(piece_response.get('duration')),
            'ext': mimetype2ext(piece_response.get('contentType')),
            'asr': int_or_none(piece_response.get('frequency'), scale=1000),
            'abr': int_or_none(piece_response.get('bitRate')),
            'url': self._extract_file_link(piece_response),
            'vcodec': 'none'
        } for piece_response in sorted(
            self._get_prx_embed_response(audio_response, 'items') or [],
            key=lambda p: int_or_none(p.get('position')))]

    def _extract_story(self, story_response):
        info = self._extract_story_info(story_response)
        if not info:
            return
        audio_pieces = self._extract_audio_pieces(
            self._get_prx_embed_response(story_response, 'audio'))
        if len(audio_pieces) == 1:
            return {
                'formats': audio_pieces,
                **info
            }

        entries = [{
            **info,
            'id': '%s_part%d' % (info['id'], (idx + 1)),
            'formats': [fmt],
        } for idx, fmt in enumerate(audio_pieces)]
        return {
            '_type': 'multi_video',
            'entries': entries,
            **info
        }

    def _real_extract(self, url):
        story_id = self._match_id(url)
        response = self._call_api(story_id, f'stories/{story_id}')
        return self._extract_story(response)


class PRXSeriesIE(PRXBaseIE):
    _VALID_URL = PRXBaseIE.PRX_BASE_URL_RE % r'series/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://beta.prx.org/series/36252',
            'info_dict': {
                'id': '36252',
                'title': 'Outside/In',
                'thumbnails': 'count:1',
                'description': 'md5:a6bedc5f810777bcb09ab30ff9059114',
                'timestamp': 1470684964,
                'modified_timestamp': 1582308830,
                'channel_id': '206',
                'channel_url': 'https://beta.prx.org/accounts/206',
                'channel': 'New Hampshire Public Radio',
                'series': 'Outside/In',
                'series_id': '36252'
            },
            'playlist_mincount': 39
        }, {
            # Blank series
            'url': 'https://beta.prx.org/series/25038',
            'info_dict': {
                'id': '25038',
                'title': '25038',
                'timestamp': 1207612800,
                'modified_timestamp': 1207612800,
                'channel_id': '206',
                'channel_url': 'https://beta.prx.org/accounts/206',
                'channel': 'New Hampshire Public Radio',
                'series': '25038',
                'series_id': '25038'
            },
            'playlist_count': 0
        }
    ]

    def _extract_series(self, series_response):
        info = self._extract_series_info(series_response)
        return {
            '_type': 'playlist',
            'entries': self._entries(info['id'], 'series/%s/stories' % info['id'], self._story_playlist_entry),
            **info
        }

    def _real_extract(self, url):
        series_id = self._match_id(url)
        response = self._call_api(series_id, f'series/{series_id}')
        return self._extract_series(response)


class PRXAccountIE(PRXBaseIE):
    _VALID_URL = PRXBaseIE.PRX_BASE_URL_RE % r'accounts/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://beta.prx.org/accounts/206',
        'info_dict': {
            'id': '206',
            'title': 'New Hampshire Public Radio',
            'description': 'md5:277f2395301d0aca563c80c70a18ee0a',
            'channel_id': '206',
            'channel_url': 'https://beta.prx.org/accounts/206',
            'channel': 'New Hampshire Public Radio',
            'thumbnails': 'count:1'
        },
        'playlist_mincount': 380
    }]

    def _extract_account(self, account_response):
        info = self._extract_account_info(account_response)
        series = self._entries(
            info['id'], f'accounts/{info["id"]}/series', self._series_playlist_entry)
        stories = self._entries(
            info['id'], f'accounts/{info["id"]}/stories', self._story_playlist_entry)
        return {
            '_type': 'playlist',
            'entries': itertools.chain(series, stories),
            **info
        }

    def _real_extract(self, url):
        account_id = self._match_id(url)
        response = self._call_api(account_id, f'accounts/{account_id}')
        return self._extract_account(response)


class PRXStoriesSearchIE(PRXBaseIE, SearchInfoExtractor):
    IE_DESC = 'PRX Stories Search'
    IE_NAME = 'prxstories:search'
    _SEARCH_KEY = 'prxstories'

    def _search_results(self, query):
        yield from self._entries(
            f'query {query}', 'stories/search', self._story_playlist_entry, query={'q': query})


class PRXSeriesSearchIE(PRXBaseIE, SearchInfoExtractor):
    IE_DESC = 'PRX Series Search'
    IE_NAME = 'prxseries:search'
    _SEARCH_KEY = 'prxseries'

    def _search_results(self, query):
        yield from self._entries(
            f'query {query}', 'series/search', self._series_playlist_entry, query={'q': query})
