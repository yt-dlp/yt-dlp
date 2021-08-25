# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    strip_or_none,
    try_get,
    urlencode_postdata,
)


class GaiaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gaia\.com/video/(?P<id>[^/?]+).*?\bfullplayer=(?P<type>feature|preview)'
    _TESTS = [{
        'url': 'https://www.gaia.com/video/connecting-universal-consciousness?fullplayer=feature',
        'info_dict': {
            'id': '89356',
            'ext': 'mp4',
            'title': 'Connecting with Universal Consciousness',
            'description': 'md5:844e209ad31b7d31345f5ed689e3df6f',
            'upload_date': '20151116',
            'timestamp': 1447707266,
            'duration': 936,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.gaia.com/video/connecting-universal-consciousness?fullplayer=preview',
        'info_dict': {
            'id': '89351',
            'ext': 'mp4',
            'title': 'Connecting with Universal Consciousness',
            'description': 'md5:844e209ad31b7d31345f5ed689e3df6f',
            'upload_date': '20151116',
            'timestamp': 1447707266,
            'duration': 53,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]
    _NETRC_MACHINE = 'gaia'
    _jwt = None

    def _real_initialize(self):
        auth = self._get_cookies('https://www.gaia.com/').get('auth')
        if auth:
            auth = self._parse_json(
                compat_urllib_parse_unquote(auth.value),
                None, fatal=False)
        if not auth:
            username, password = self._get_login_info()
            if username is None:
                return
            auth = self._download_json(
                'https://auth.gaia.com/v1/login',
                None, data=urlencode_postdata({
                    'username': username,
                    'password': password
                }))
            if auth.get('success') is False:
                raise ExtractorError(', '.join(auth['messages']), expected=True)
        if auth:
            self._jwt = auth.get('jwt')

    def _real_extract(self, url):
        display_id, vtype = self._match_valid_url(url).groups()
        node_id = self._download_json(
            'https://brooklyn.gaia.com/pathinfo', display_id, query={
                'path': 'video/' + display_id,
            })['id']
        node = self._download_json(
            'https://brooklyn.gaia.com/node/%d' % node_id, node_id)
        vdata = node[vtype]
        media_id = compat_str(vdata['nid'])
        title = node['title']

        headers = None
        if self._jwt:
            headers = {'Authorization': 'Bearer ' + self._jwt}
        media = self._download_json(
            'https://brooklyn.gaia.com/media/' + media_id,
            media_id, headers=headers)
        formats = self._extract_m3u8_formats(
            media['mediaUrls']['bcHLS'], media_id, 'mp4')
        self._sort_formats(formats)

        subtitles = {}
        text_tracks = media.get('textTracks', {})
        for key in ('captions', 'subtitles'):
            for lang, sub_url in text_tracks.get(key, {}).items():
                subtitles.setdefault(lang, []).append({
                    'url': sub_url,
                })

        fivestar = node.get('fivestar', {})
        fields = node.get('fields', {})

        def get_field_value(key, value_key='value'):
            return try_get(fields, lambda x: x[key][0][value_key])

        return {
            'id': media_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'description': strip_or_none(get_field_value('body') or get_field_value('teaser')),
            'timestamp': int_or_none(node.get('created')),
            'subtitles': subtitles,
            'duration': int_or_none(vdata.get('duration')),
            'like_count': int_or_none(try_get(fivestar, lambda x: x['up_count']['value'])),
            'dislike_count': int_or_none(try_get(fivestar, lambda x: x['down_count']['value'])),
            'comment_count': int_or_none(node.get('comment_count')),
            'series': try_get(node, lambda x: x['series']['title'], compat_str),
            'season_number': int_or_none(get_field_value('season')),
            'season_id': str_or_none(get_field_value('series_nid', 'nid')),
            'episode_number': int_or_none(get_field_value('episode')),
        }
