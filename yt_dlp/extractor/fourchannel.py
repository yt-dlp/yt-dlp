# encoding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    try_get,
)


class FourChannelIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)boards.4channel.org/(?P<board>[^/]+)/thread/(?P<thread_id>\d+)'
    _TESTS = [{
        # This test will break in future once the thread gets removed even from the archives.
        'url': 'https://boards.4channel.org/wsg/thread/4088700',
        'info_dict': {
            'id': '4088700',
        },
        'playlist_mincount': 33,
    }, {
        # This is a stickied post so this should last forever hopefully.
        'url': 'https://boards.4channel.org/k/thread/23385784',
        'info_dict': {
            'id': '1',
        },
        'playlist_mincount': 20000,
    }]

    def _entries(self, board, id):
        thread_json = self._download_json(f'https://a.4cdn.org/{board}/thread/{id}.json', id)
        posts = thread_json.get('posts', [])
        thread_subject = try_get(posts, lambda x: x[0]['sub'])
        for post in posts:
            post_id = post.get('tim')
            ext = post.get('ext', '')
            if post_id:
                post_id = str(post_id)
                yield {
                    'id': post_id,
                    'ext': ext[1:],
                    'title': post.get('filename'),
                    'width': post.get('w'),
                    'height': post.get('h'),
                    'url': f'https://i.4cdn.org/{board}/{post_id}{ext}',
                    'uploader': post.get('name'),
                    'description': clean_html(post.get('com')),
                    'series': board,
                    'season_id': id,
                    'season': thread_subject,
                }

    def _real_extract(self, url):
        board, id = self._match_valid_url(url).groups()
        return self.playlist_result(self._entries(board, id), playlist_id=id)
