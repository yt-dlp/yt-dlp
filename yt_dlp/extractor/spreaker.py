# coding: utf-8
from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    int_or_none,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)


def _extract_episode(data, episode_id=None):
    title = data['title']
    download_url = data['download_url']

    series = try_get(data, lambda x: x['show']['title'], compat_str)
    uploader = try_get(data, lambda x: x['author']['fullname'], compat_str)

    thumbnails = []
    for image in ('image_original', 'image_medium', 'image'):
        image_url = url_or_none(data.get('%s_url' % image))
        if image_url:
            thumbnails.append({'url': image_url})

    def stats(key):
        return int_or_none(try_get(
            data,
            (lambda x: x['%ss_count' % key],
             lambda x: x['stats']['%ss' % key])))

    def duration(key):
        return float_or_none(data.get(key), scale=1000)

    return {
        'id': compat_str(episode_id or data['episode_id']),
        'url': download_url,
        'display_id': data.get('permalink'),
        'title': title,
        'description': data.get('description'),
        'timestamp': unified_timestamp(data.get('published_at')),
        'uploader': uploader,
        'uploader_id': str_or_none(data.get('author_id')),
        'creator': uploader,
        'duration': duration('duration') or duration('length'),
        'view_count': stats('play'),
        'like_count': stats('like'),
        'comment_count': stats('message'),
        'format': 'MPEG Layer 3',
        'format_id': 'mp3',
        'container': 'mp3',
        'ext': 'mp3',
        'thumbnails': thumbnails,
        'series': series,
        'extractor_key': SpreakerIE.ie_key(),
    }


class SpreakerIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        api\.spreaker\.com/
                        (?:
                            (?:download/)?episode|
                            v2/episodes
                        )/
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://api.spreaker.com/episode/12534508',
        'info_dict': {
            'id': '12534508',
            'display_id': 'swm-ep15-how-to-market-your-music-part-2',
            'ext': 'mp3',
            'title': 'EP:15 | Music Marketing (Likes) - Part 2',
            'description': 'md5:0588c43e27be46423e183076fa071177',
            'timestamp': 1502250336,
            'upload_date': '20170809',
            'uploader': 'SWM',
            'uploader_id': '9780658',
            'duration': 1063.42,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'series': 'Success With Music (SWM)',
        },
    }, {
        'url': 'https://api.spreaker.com/download/episode/12534508/swm_ep15_how_to_market_your_music_part_2.mp3',
        'only_matching': True,
    }, {
        'url': 'https://api.spreaker.com/v2/episodes/12534508?export=episode_segments',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        data = self._download_json(
            'https://api.spreaker.com/v2/episodes/%s' % episode_id,
            episode_id)['response']['episode']
        return _extract_episode(data, episode_id)


class SpreakerPageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?spreaker\.com/user/[^/]+/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.spreaker.com/user/9780658/swm-ep15-how-to-market-your-music-part-2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        episode_id = self._search_regex(
            (r'data-episode_id=["\'](?P<id>\d+)',
             r'episode_id\s*:\s*(?P<id>\d+)'), webpage, 'episode id')
        return self.url_result(
            'https://api.spreaker.com/episode/%s' % episode_id,
            ie=SpreakerIE.ie_key(), video_id=episode_id)


class SpreakerShowIE(InfoExtractor):
    _VALID_URL = r'https?://api\.spreaker\.com/show/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://api.spreaker.com/show/4652058',
        'info_dict': {
            'id': '4652058',
        },
        'playlist_mincount': 118,
    }]

    def _entries(self, show_id):
        for page_num in itertools.count(1):
            episodes = self._download_json(
                'https://api.spreaker.com/show/%s/episodes' % show_id,
                show_id, note='Downloading JSON page %d' % page_num, query={
                    'page': page_num,
                    'max_per_page': 100,
                })
            pager = try_get(episodes, lambda x: x['response']['pager'], dict)
            if not pager:
                break
            results = pager.get('results')
            if not results or not isinstance(results, list):
                break
            for result in results:
                if not isinstance(result, dict):
                    continue
                yield _extract_episode(result)
            if page_num == pager.get('last_page'):
                break

    def _real_extract(self, url):
        show_id = self._match_id(url)
        return self.playlist_result(self._entries(show_id), playlist_id=show_id)


class SpreakerShowPageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?spreaker\.com/show/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.spreaker.com/show/success-with-music',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        show_id = self._search_regex(
            r'show_id\s*:\s*(?P<id>\d+)', webpage, 'show id')
        return self.url_result(
            'https://api.spreaker.com/show/%s' % show_id,
            ie=SpreakerShowIE.ie_key(), video_id=show_id)
