from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    clean_html,
    int_or_none,
    float_or_none,
)


def _decrypt_config(key, string):
    a = ''
    i = ''
    r = ''

    while len(a) < (len(string) / 2):
        a += key

    a = a[0:int(len(string) / 2)]

    t = 0
    while t < len(string):
        i += chr(int(string[t] + string[t + 1], 16))
        t += 2

    icko = [s for s in i]

    for t, c in enumerate(a):
        r += chr(ord(c) ^ ord(icko[t]))

    return r


class EscapistIE(InfoExtractor):
    _VALID_URL = r'https?://?(?:(?:www|v1)\.)?escapistmagazine\.com/videos/view/[^/]+/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.escapistmagazine.com/videos/view/the-escapist-presents/6618-Breaking-Down-Baldurs-Gate',
        'md5': 'ab3a706c681efca53f0a35f1415cf0d1',
        'info_dict': {
            'id': '6618',
            'ext': 'mp4',
            'description': "Baldur's Gate: Original, Modded or Enhanced Edition? I'll break down what you can expect from the new Baldur's Gate: Enhanced Edition.",
            'title': "Breaking Down Baldur's Gate",
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 264,
            'uploader': 'The Escapist',
        }
    }, {
        'url': 'http://www.escapistmagazine.com/videos/view/zero-punctuation/10044-Evolve-One-vs-Multiplayer',
        'md5': '9e8c437b0dbb0387d3bd3255ca77f6bf',
        'info_dict': {
            'id': '10044',
            'ext': 'mp4',
            'description': 'This week, Zero Punctuation reviews Evolve.',
            'title': 'Evolve - One vs Multiplayer',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 304,
            'uploader': 'The Escapist',
        }
    }, {
        'url': 'http://escapistmagazine.com/videos/view/the-escapist-presents/6618',
        'only_matching': True,
    }, {
        'url': 'https://v1.escapistmagazine.com/videos/view/the-escapist-presents/6618-Breaking-Down-Baldurs-Gate',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        ims_video = self._parse_json(
            self._search_regex(
                r'imsVideo\.play\(({.+?})\);', webpage, 'imsVideo'),
            video_id)
        video_id = ims_video['videoID']
        key = ims_video['hash']

        config = self._download_webpage(
            'http://www.escapistmagazine.com/videos/vidconfig.php',
            video_id, 'Downloading video config', headers={
                'Referer': url,
            }, query={
                'videoID': video_id,
                'hash': key,
            })

        data = self._parse_json(_decrypt_config(key, config), video_id)

        video_data = data['videoData']

        title = clean_html(video_data['title'])

        formats = [{
            'url': video['src'],
            'format_id': '%s-%sp' % (determine_ext(video['src']), video['res']),
            'height': int_or_none(video.get('res')),
        } for video in data['files']['videos']]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage) or data.get('poster'),
            'description': self._og_search_description(webpage),
            'duration': float_or_none(video_data.get('duration'), 1000),
            'uploader': video_data.get('publisher'),
            'series': video_data.get('show'),
        }
