# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .vk import VKIE
from ..compat import compat_b64decode

from ..utils import (
    int_or_none,
    js_to_json,
    traverse_obj,
    unified_timestamp,
)


class BIQLEIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?biqle\.(?:com|org|ru)/watch/(?P<id>-?\d+_\d+)'
    _TESTS = [{
        'url': 'https://biqle.ru/watch/-2000421746_85421746',
        'md5': 'ae6ef4f04d19ac84e4658046d02c151c',
        'info_dict': {
            'id': '-2000421746_85421746',
            'ext': 'mp4',
            'title': 'Forsaken By Hope Studio Clip',
            'description': 'Forsaken By Hope Studio Clip — Смотреть онлайн',
            'upload_date': '19700101',
            'timestamp': 0,
            'thumbnail': r're:https://[^/]+/impf/7vN3ACwSTgChP96OdOfzFjUCzFR6ZglDQgWsIw/KPaACiVJJxM\.jpg\?size=800x450&quality=96&keep_aspect_ratio=1&background=000000&sign=b48ea459c4d33dbcba5e26d63574b1cb&type=video_thumb',
        },
    }, {
        'url': 'http://biqle.org/watch/-44781847_168547604',
        'md5': '7f24e72af1db0edf7c1aaba513174f97',
        'info_dict': {
            'id': '-44781847_168547604',
            'ext': 'mp4',
            'title': 'Ребенок в шоке от автоматической мойки',
            'description': 'Ребенок в шоке от автоматической мойки — Смотреть онлайн',
            'timestamp': 1396633454,
            'upload_date': '20140404',
            'thumbnail': r're:https://[^/]+/c535507/u190034692/video/l_b84df002\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._search_regex(
            r'<meta.*itemprop ?= ?"name".*content ?= ?"([^"]+)".*/>',
            webpage, 'Title', default='Empty Title', fatal=False)
        uploadDate = self._search_regex(
            r'<meta.*itemprop ?= ?"uploadDate".*content ?= ?"([^"]+)".*/?>',
            webpage, 'Upload Date', fatal=False)
        timestamp = unified_timestamp(uploadDate)
        description = self._search_regex(
            r'<meta.*itemprop ?= ?"description".*content ?= ?"([^"]+)".*/>',
            webpage, 'Description', fatal=False)

        globalEmbed_url = self._search_regex(
            r'<script.+?window.globEmbedUrl = \'((?:https?:)?//(?:daxab\.com|dxb\.to|[^/]+/player)/[^\']+)\'.*?></script>',
            webpage, 'global Embed url', flags=re.DOTALL)
        hash = self._search_regex(
            r'<script id="data-embed-video.+?hash: "([^"]+)"[^<]*</script>',
            webpage, 'Hash', flags=re.DOTALL)

        embed_url = globalEmbed_url + hash

        if VKIE.suitable(embed_url):
            return self.url_result(embed_url, VKIE.ie_key(), video_id)

        embed_page = self._download_webpage(
            embed_url, video_id, 'Downloading embed webpage', headers={'Referer': url})

        globParams = self._parse_json(self._search_regex(
            r'<script id="globParams">.*window.globParams = ([^;]+);[^<]+</script>',
            embed_page, 'Global Parameters', flags=re.DOTALL), video_id, transform_source=js_to_json)
        hostName = compat_b64decode(globParams['server'][::-1]).decode()
        server = 'https://%s/method/video.get/' % hostName

        item = self._download_json(
            server + video_id, video_id,
            headers={'Referer': url}, query={
                'token': globParams['video']['access_token'],
                'videos': video_id,
                'ckey': globParams['c_key'],
                'credentials': globParams['video']['credentials'],
            })['response']['items'][0]

        formats = []
        for f_id, f_url in item.get('files', {}).items():
            if f_id == 'external':
                return self.url_result(f_url)
            ext, height = f_id.split('_')
            if traverse_obj(globParams, ('video', 'partial', 'quality', height)) is not None:
                formats.append({
                    'format_id': height + 'p',
                    'url': f'https://{hostName}/{f_url[8:]}&videos={video_id}&extra_key={globParams["video"]["partial"]["quality"][height]}',
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
            'description': description,
            'duration': int_or_none(item.get('duration')),
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'view_count': int_or_none(item.get('views')),
        }
