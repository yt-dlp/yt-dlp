# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .vk import VKIE
from ..compat import (
    compat_b64decode,
    compat_urllib_parse_unquote,
)
from ..utils import int_or_none


class BIQLEIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?biqle\.(?:com|org|ru)/watch/(?P<id>-?\d+_\d+)'
    _TESTS = [{
        # Youtube embed
        'url': 'https://biqle.ru/watch/-115995369_456239081',
        'md5': '97af5a06ee4c29bbf9c001bdb1cf5c06',
        'info_dict': {
            'id': '8v4f-avW-VI',
            'ext': 'mp4',
            'title': "PASSE-PARTOUT - L'ete c'est fait pour jouer",
            'description': 'Passe-Partout',
            'uploader_id': 'mrsimpsonstef3',
            'uploader': 'Phanolito',
            'upload_date': '20120822',
        },
    }, {
        'url': 'http://biqle.org/watch/-44781847_168547604',
        'md5': '7f24e72af1db0edf7c1aaba513174f97',
        'info_dict': {
            'id': '-44781847_168547604',
            'ext': 'mp4',
            'title': 'Ребенок в шоке от автоматической мойки',
            'timestamp': 1396633454,
            'uploader': 'Dmitry Kotov',
            'upload_date': '20140404',
            'uploader_id': '47850140',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        embed_url = self._proto_relative_url(self._search_regex(
            r'<iframe.+?src="((?:https?:)?//(?:daxab\.com|dxb\.to|[^/]+/player)/[^"]+)".*?></iframe>',
            webpage, 'embed url'))
        if VKIE.suitable(embed_url):
            return self.url_result(embed_url, VKIE.ie_key(), video_id)

        embed_page = self._download_webpage(
            embed_url, video_id, headers={'Referer': url})
        video_ext = self._get_cookies(embed_url).get('video_ext')
        if video_ext:
            video_ext = compat_urllib_parse_unquote(video_ext.value)
        if not video_ext:
            video_ext = compat_b64decode(self._search_regex(
                r'video_ext\s*:\s*[\'"]([A-Za-z0-9+/=]+)',
                embed_page, 'video_ext')).decode()
        video_id, sig, _, access_token = video_ext.split(':')
        item = self._download_json(
            'https://api.vk.com/method/video.get', video_id,
            headers={'User-Agent': 'okhttp/3.4.1'}, query={
                'access_token': access_token,
                'sig': sig,
                'v': 5.44,
                'videos': video_id,
            })['response']['items'][0]
        title = item['title']

        formats = []
        for f_id, f_url in item.get('files', {}).items():
            if f_id == 'external':
                return self.url_result(f_url)
            ext, height = f_id.split('_')
            formats.append({
                'format_id': height + 'p',
                'url': f_url,
                'height': int_or_none(height),
                'ext': ext,
            })
        self._sort_formats(formats)

        thumbnails = []
        for k, v in item.items():
            if k.startswith('photo_') and v:
                width = k.replace('photo_', '')
                thumbnails.append({
                    'id': width,
                    'url': v,
                    'width': int_or_none(width),
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'comment_count': int_or_none(item.get('comments')),
            'description': item.get('description'),
            'duration': int_or_none(item.get('duration')),
            'thumbnails': thumbnails,
            'timestamp': int_or_none(item.get('date')),
            'uploader': item.get('owner_id'),
            'view_count': int_or_none(item.get('views')),
        }
