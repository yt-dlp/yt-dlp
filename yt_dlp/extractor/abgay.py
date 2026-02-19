import json
import math
import re
import urllib.parse

from .common import InfoExtractor


class ABGayExtractorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?abgay\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://abgay.com/video/231752/jan-10-2023-a-long-sweaty-relaxing-vacpacking-in-my-shiny-ski-jacket-pvc-aprons-amp-lead-aprons/',
        'md5': '67cf691be29f214d8d2d0dbd525fa7ba',
        'info_dict': {
            'id': '231752',
            'ext': 'mp4',
            'title': 'Jan 10 2023 - A Long Sweaty Relaxing Vacpacking In My Shiny Ski Jacket Pvc Aprons &amp; Lead Aprons',
            'uploader': 'Tobias Morgan',
            'view_count': int,
        },
    }]

    def _decode_b164(self, e):

        t = 'АВСDЕFGHIJKLМNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,~'
        A = ''
        n = 0

        if re.search(r'[^АВСЕМA-Za-z0-9\.\,\~]', e):
            raise Exception('error decoding url')

        e = re.sub(r'[^АВСЕМA-Za-z0-9\.\,\~]', '', e)

        while True:
            o = t.find(e[n]) if n < len(e) else 64
            n += 1
            r = t.find(e[n]) if n < len(e) else 64
            n += 1
            a = t.find(e[n]) if n < len(e) else 64
            n += 1
            i = t.find(e[n]) if n < len(e) else 64
            n += 1

            # Perform the base64 decoding
            o = (o << 2) | (r >> 4)
            r = ((15 & r) << 4) | (a >> 2)
            c = ((3 & a) << 6) | i

            # Append the decoded characters
            A += chr(o)
            if a != 64:  # Not padding
                A += chr(r)
            if i != 64:  # Not padding
                A += chr(c)

            if n >= len(e):
                break
        return urllib.parse.unquote(A)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        line = next((line for line in webpage.splitlines() if 'window.constants' in line and 'lifetime' in line), None)
        constants_json = json.loads(line.split('=')[1].strip())
        lifetime = constants_json['query']['lifetime']

        video_id = int(video_id)
        n = str(1000000 * math.floor(video_id / 1000000)) + '/' + str(1000 * math.floor(video_id / 1000))

        meta_url = f'https://abgay.com/api/json/video/{lifetime}/{n}/{video_id}.json'
        meta_json = json.loads(self._download_webpage(meta_url, video_id))
        title = meta_json['video']['title']
        view_count = meta_json['video']['statistics']['viewed']
        uploader = meta_json['video']['user']['username']

        meta_url = f'https://abgay.com/api/videofile.php?video_id={video_id}&lifetime={lifetime}00'
        meta_json = json.loads(self._download_webpage(meta_url, video_id))[0]
        file_format = meta_json['format']
        video_url = 'https://abgay.com' + self._decode_b164(meta_json['video_url'])

        return {
            'id': str(video_id),
            'title': title,
            'uploader': uploader,
            'view_count': int(view_count),
            'formats': [{
                'url': video_url,
                'ext': file_format.strip('.'),
            }],
        }
