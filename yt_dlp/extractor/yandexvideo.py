# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    try_get,
    url_or_none,
)


class YandexVideoIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            yandex\.ru(?:/(?:portal/(?:video|efir)|efir))?/?\?.*?stream_id=|
                            frontend\.vh\.yandex\.ru/player/
                        )
                        (?P<id>(?:[\da-f]{32}|[\w-]{12}))
                    '''
    _TESTS = [{
        'url': 'https://yandex.ru/portal/video?stream_id=4dbb36ec4e0526d58f9f2dc8f0ecf374',
        'md5': 'e02a05bfaf0d9615ef07ae3a10f4faf4',
        'info_dict': {
            'id': '4dbb36ec4e0526d58f9f2dc8f0ecf374',
            'ext': 'mp4',
            'title': 'Русский Вудсток - главный рок-фест в истории СССР / вДудь',
            'description': 'md5:7d6b8d4bc4a3b9a56499916c1ea5b5fa',
            'thumbnail': r're:^https?://',
            'timestamp': 1549972939,
            'duration': 5575,
            'age_limit': 18,
            'upload_date': '20190212',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
        },
    }, {
        'url': 'https://yandex.ru/portal/efir?stream_id=4dbb262b4fe5cf15a215de4f34eee34d&from=morda',
        'only_matching': True,
    }, {
        'url': 'https://yandex.ru/?stream_id=4dbb262b4fe5cf15a215de4f34eee34d',
        'only_matching': True,
    }, {
        'url': 'https://frontend.vh.yandex.ru/player/4dbb262b4fe5cf15a215de4f34eee34d?from=morda',
        'only_matching': True,
    }, {
        # vod-episode, series episode
        'url': 'https://yandex.ru/portal/video?stream_id=45b11db6e4b68797919c93751a938cee',
        'only_matching': True,
    }, {
        # episode, sports
        'url': 'https://yandex.ru/?stream_channel=1538487871&stream_id=4132a07f71fb0396be93d74b3477131d',
        'only_matching': True,
    }, {
        # DASH with DRM
        'url': 'https://yandex.ru/portal/video?from=morda&stream_id=485a92d94518d73a9d0ff778e13505f8',
        'only_matching': True,
    }, {
        'url': 'https://yandex.ru/efir?stream_active=watching&stream_id=v7a2dZ-v5mSI&from_block=efir_newtab',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player = try_get((self._download_json(
            'https://frontend.vh.yandex.ru/graphql', video_id, data=('''{
  player(content_id: "%s") {
    computed_title
    content_url
    description
    dislikes
    duration
    likes
    program_title
    release_date
    release_date_ut
    release_year
    restriction_age
    season
    start_time
    streams
    thumbnail
    title
    views_count
  }
}''' % video_id).encode(), fatal=False)), lambda x: x['player']['content'])
        if not player or player.get('error'):
            player = self._download_json(
                'https://frontend.vh.yandex.ru/v23/player/%s.json' % video_id,
                video_id, query={
                    'stream_options': 'hires',
                    'disable_trackings': 1,
                })
        content = player['content']

        title = content.get('title') or content['computed_title']

        formats = []
        streams = content.get('streams') or []
        streams.append({'url': content.get('content_url')})
        for stream in streams:
            content_url = url_or_none(stream.get('url'))
            if not content_url:
                continue
            ext = determine_ext(content_url)
            if ext == 'ismc':
                continue
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    content_url, video_id, 'mp4',
                    'm3u8_native', m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    content_url, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({'url': content_url})

        self._sort_formats(formats)

        timestamp = (int_or_none(content.get('release_date'))
                     or int_or_none(content.get('release_date_ut'))
                     or int_or_none(content.get('start_time')))
        season = content.get('season') or {}

        return {
            'id': video_id,
            'title': title,
            'description': content.get('description'),
            'thumbnail': content.get('thumbnail'),
            'timestamp': timestamp,
            'duration': int_or_none(content.get('duration')),
            'series': content.get('program_title'),
            'age_limit': int_or_none(content.get('restriction_age')),
            'view_count': int_or_none(content.get('views_count')),
            'like_count': int_or_none(content.get('likes')),
            'dislike_count': int_or_none(content.get('dislikes')),
            'season_number': int_or_none(season.get('season_number')),
            'season_id': season.get('id'),
            'release_year': int_or_none(content.get('release_year')),
            'formats': formats,
        }


class ZenYandexIE(InfoExtractor):
    _VALID_URL = r'https?://zen\.yandex\.ru/media/(?:id/[^/]+/|[^/]+/)(?:[a-z0-9-]+)-(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://zen.yandex.ru/media/popmech/izverjenie-vulkana-iz-spichek-zreliscnyi-opyt-6002240ff8b1af50bb2da5e3',
        'info_dict': {
            'id': '6002240ff8b1af50bb2da5e3',
            'ext': 'mp4',
            'title': 'Извержение вулкана из спичек: зрелищный опыт',
            'description': 'md5:053ad3c61b5596d510c9a199dc8ee633',
            'thumbnail': 'https://avatars.mds.yandex.net/get-zen-pub-og/3558619/pub_6002240ff8b1af50bb2da5e3_600bad814d953e4132a30b5e/orig',
            'uploader': 'Популярная механика',
        },
    }, {
        'url': 'https://zen.yandex.ru/media/id/606fd806cc13cb3c58c05cf5/vot-eto-focus-dedy-morozy-na-gidrociklah-60c7c443da18892ebfe85ed7',
        'info_dict': {
            'id': '60c7c443da18892ebfe85ed7',
            'ext': 'mp4',
            'title': 'ВОТ ЭТО Focus. Деды Морозы на гидроциклах',
            'description': 'md5:8684912f6086f298f8078d4af0e8a600',
            'thumbnail': 'https://avatars.mds.yandex.net/get-zen-pub-og/4410519/pub_60c7c443da18892ebfe85ed7_60c7c48e060a163121f42cc3/orig',
            'uploader': 'AcademeG DailyStream'
        },
    }, {
        'url': 'https://zen.yandex.ru/media/id/606fd806cc13cb3c58c05cf5/novyi-samsung-fold-3-moskvich-barahlit-612f93b7f8d48e7e945792a2?from=channel&rid=2286618386.482.1630817595976.42360',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._search_regex(r'w\._data\s?=\s?({.+?});', webpage, 'metadata'), id)
        stream_json = try_get(data_json, lambda x: x['publication']['content']['gifContent'], dict)
        stream_url = stream_json.get('stream') or try_get(stream_json, lambda x: x['streams']['url'])
        formats = self._extract_m3u8_formats(stream_url, id)
        self._sort_formats(formats)
        return {
            'id': id,
            'title': try_get(data_json, (lambda x: x['og']['title'], lambda x: x['publication']['content']['preview']['title'])),
            'uploader': data_json.get('authorName') or try_get(data_json, lambda x: x['publisher']['name']),
            'description': try_get(data_json, lambda x: x['og']['description']),
            'thumbnail': try_get(data_json, lambda x: x['og']['imageUrl']),
            'formats': formats,
        }


class ZenYandexChannelIE(InfoExtractor):
    _VALID_URL = r'https?://zen\.yandex\.ru/(?!media)(?:id/)?(?P<id>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://zen.yandex.ru/tok_media',
        'info_dict': {
            'id': 'tok_media',
        },
        'playlist_mincount': 169,
    }, {
        'url': 'https://zen.yandex.ru/id/606fd806cc13cb3c58c05cf5',
        'info_dict': {
            'id': '606fd806cc13cb3c58c05cf5',
        },
        'playlist_mincount': 657,
    }]

    def _entries(self, id, url):
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(re.findall(r'var\s?data\s?=\s?({.+?})\s?;', webpage)[-1], id)
        for key in data_json.keys():
            if key.startswith('__serverState__'):
                data_json = data_json[key]
        items = list(try_get(data_json, lambda x: x['feed']['items'], dict).values())
        more = try_get(data_json, lambda x: x['links']['more']) or None
        for page in itertools.count(1):
            for item in items:
                video_id = item.get('publication_id') or item.get('publicationId')
                video_url = item.get('link')
                yield self.url_result(video_url, ie=ZenYandexIE.ie_key(), video_id=video_id.split(':')[-1])
            if not more:
                break
            data_json = self._download_json(more, id, note='Downloading Page %d' % page)
            items = data_json.get('items', [])
            more = try_get(data_json, lambda x: x['more']['link']) or None

    def _real_extract(self, url):
        id = self._match_id(url)
        return self.playlist_result(self._entries(id, url), playlist_id=id)
