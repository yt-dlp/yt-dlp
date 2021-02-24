# coding: utf-8
from __future__ import unicode_literals

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
