import base64
import json
import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    js_to_json,
    remove_start,
)


class JStreamIE(InfoExtractor):
    # group "id" only exists for compliance, not directly used in requests
    # also all components are mandatory
    _VALID_URL = r'jstream:(?P<host>www\d+):(?P<id>(?P<publisher>[a-z0-9]+):(?P<mid>\d+))'

    _TESTS = [{
        'url': 'jstream:www50:eqd638pvwx:752',
        'info_dict': {
            'id': 'eqd638pvwx:752',
            'ext': 'mp4',
            'title': '阪神淡路大震災 激震の記録2020年版　解説動画',
            'duration': 672,
            'thumbnail': r're:https?://eqd638pvwx\.eq\.webcdn\.stream\.ne\.jp/.+\.jpg',
        },
    }]

    def _parse_jsonp(self, callback, string, video_id):
        return self._search_json(rf'\s*{re.escape(callback)}\s*\(', string, callback, video_id)

    def _find_formats(self, video_id, movie_list_hls, host, publisher, subtitles):
        for value in movie_list_hls:
            text = value.get('text') or ''
            if not text.startswith('auto'):
                continue
            m3u8_id = remove_start(remove_start(text, 'auto'), '_') or None
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                f'https://{publisher}.eq.webcdn.stream.ne.jp/{host}/{publisher}/jmc_pub/{value.get("url")}', video_id, 'mp4', m3u8_id=m3u8_id)
            self._merge_subtitles(subs, target=subtitles)
            yield from fmts

    def _real_extract(self, url):
        host, publisher, mid, video_id = self._match_valid_url(url).group('host', 'publisher', 'mid', 'id')
        video_info_jsonp = self._download_webpage(
            f'https://{publisher}.eq.webcdn.stream.ne.jp/{host}/{publisher}/jmc_pub/eq_meta/v1/{mid}.jsonp',
            video_id, 'Requesting video info')
        video_info = self._parse_jsonp('metaDataResult', video_info_jsonp, video_id)['movie']
        subtitles = {}
        formats = list(self._find_formats(video_id, video_info.get('movie_list_hls'), host, publisher, subtitles))
        self._remove_duplicate_formats(formats)
        return {
            'id': video_id,
            'title': video_info.get('title'),
            'duration': float_or_none(video_info.get('duration')),
            'thumbnail': video_info.get('thumbnail_url'),
            'formats': formats,
            'subtitles': subtitles,
        }

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # check for eligiblity of webpage
        # https://support.eq.stream.co.jp/hc/ja/articles/115008388147-%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A4%E3%83%BCAPI%E3%81%AE%E3%82%B5%E3%83%B3%E3%83%97%E3%83%AB%E3%82%B3%E3%83%BC%E3%83%89
        script_tag = re.search(r'<script\s*[^>]+?src="https://ssl-cache\.stream\.ne\.jp/(?P<host>www\d+)/(?P<publisher>[a-z0-9]+)/[^"]+?/if\.js"', webpage)
        if not script_tag:
            return
        host, publisher = script_tag.groups()
        for m in re.finditer(r'(?s)PlayerFactoryIF\.create\(\s*({[^\}]+?})\s*\)\s*;', webpage):
            # TODO: using json.loads here as InfoExtractor._parse_json is not classmethod
            info = json.loads(js_to_json(m.group(1)))
            mid = base64.b64decode(info.get('m')).decode()
            yield f'jstream:{host}:{publisher}:{mid}'
