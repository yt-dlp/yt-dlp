import json

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    mimetype2ext,
    parse_qs,
    str_or_none,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import require, traverse_obj


class BloggerIE(InfoExtractor):
    _ITAG_MAP = {
        '7': (320, 240),
        '18': (640, 360),
        '22': (1280, 720),
        '37': (1920, 1080),
    }
    _RPC_ID = 'WcwnYd'
    _VALID_URL = r'https?://(?:www\.)?blogger\.com/video\.g\?(?:[^#]+&)?token=(?P<id>[\w-]+)'
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc\s*=\s*(["\'])(?P<url>(?:https?:)?//(?:www\.)?blogger\.com/video\.g\?(?:[^#"\']+&)?token=[^"\']+)\1']
    _TESTS = [{
        'url': 'https://www.blogger.com/video.g?token=AD6v5dzEe9hfcARr5Hlq1WTkYy6t-fXH3BBahVhGvVHe5szdEUBEloSEDSTA8-b111089KbfWuBvTN7fnbxMtymsHhXAXwVvyzHH4Qch2cfLQdGxKQrrEuFpC1amSl_9GuLWODjPgw',
        'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
        'info_dict': {
            'id': '3c740e3a49197e16',
            'ext': 'mp4',
            'title': 'BLOGGER-video-3c740e3a49197e16-796',
            'duration': 76.068,
            'thumbnail': r're:https?://i9\.ytimg\.com/vi_blogger/.+',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://blog.tomeuvizoso.net/2019/01/a-panfrost-milestone.html',
        'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
        'info_dict': {
            'id': '3c740e3a49197e16',
            'ext': 'mp4',
            'title': r're:BLOGGER-video-3c740e3a49197e16-\d+',
            'duration': 76.068,
            'thumbnail': r're:https?://i9\.ytimg\.com/vi_blogger/.+',
        },
    }]

    def _extract_rpc_data(self, webpage, token_id):
        wiz_global_data = self._search_json(
            r'window\.WIZ_global_data\s*=', webpage, 'wiz global data', None)
        f_sid = traverse_obj(wiz_global_data, (
            'FdrFJe', {str_or_none}, {require('f.sid')}))
        bl = traverse_obj(wiz_global_data, (
            'cfb2h', {str_or_none}, {require('build label')}))

        f_req = json.dumps([[[
            self._RPC_ID, json.dumps([
                token_id, None, 0,
            ], separators=(',', ':')),
            None, 'generic',
        ]]], separators=(',', ':'))

        player_data = self._download_webpage(
            'https://www.blogger.com/_/BloggerVideoPlayerUi/data/batchexecute',
            None, query={
                'bl': bl,
                'f.sid': f_sid,
                'rpcids': self._RPC_ID,
            }, data=urlencode_postdata({'f.req': f_req}))

        for line in player_data.splitlines():
            line = line.strip()
            if not line.startswith('['):
                continue

            parsed_line = self._parse_json(line, None, fatal=False)
            if payload := traverse_obj(parsed_line, (
                lambda _, v: v[0] == 'wrb.fr' and v[1] == self._RPC_ID,
                2, {str}, any,
            )):
                rpc_data = self._parse_json(payload, None, fatal=False)
                if isinstance(rpc_data, list):
                    return rpc_data

    def _extract_formats(self, rpc_data):
        formats = []

        for stream in traverse_obj(rpc_data, (
            2, lambda _, v: url_or_none(v[0]),
        )):
            video_url = stream[0]
            query = parse_qs(video_url)
            itag = traverse_obj(query, ('itag', -1, {str_or_none}))
            width, height = self._ITAG_MAP.get(itag) or (320, 240)

            formats.append({
                'format_id': itag,
                'height': height,
                'url': video_url,
                'width': width,
                **traverse_obj(query, {
                    'duration': ('dur', -1, {float_or_none}),
                    'ext': ('mime', -1, {mimetype2ext}),
                    'filesize': ('clen', -1, {int_or_none}),
                }),
            })

        return formats

    def _real_extract(self, url):
        token_id = self._match_id(url)
        webpage = self._download_webpage(url, None)
        rpc_data = self._extract_rpc_data(webpage, token_id)

        return {
            'formats': self._extract_formats(rpc_data),
            **traverse_obj(rpc_data, {
                'id': (5, {str_or_none}),
                'title': (4, {clean_html}, filter),
                'thumbnail': (3, {url_or_none}),
            }),
        }
