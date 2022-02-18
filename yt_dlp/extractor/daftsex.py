# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .vk import VKIE
from ..compat import compat_b64decode
from ..utils import (
    get_elements_by_class,
    int_or_none,
    js_to_json,
    parse_count,
    parse_duration,
    traverse_obj,
    try_get,
    unified_timestamp,
)


class DaftsexIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?daftsex\.com/watch/(?P<id>-?\d+_\d+)'
    _TESTS = [{
        'url': 'https://daftsex.com/watch/-35370899_456246186',
        'md5': 'd95135e6cea2d905bea20dbe82cda64a',
        'info_dict': {
            'id': '-35370899_456246186',
            'ext': 'mp4',
            'title': 'just relaxing',
            'description': 'just relaxing - Watch video Watch video in high quality',
            'upload_date': '20201113',
            'timestamp': 1605261911,
            'thumbnail': r're:https://[^/]+/impf/-43BuMDIawmBGr3GLcZ93CYwWf2PBv_tVWoS1A/dnu41DnARU4\.jpg\?size=800x450&quality=96&keep_aspect_ratio=1&background=000000&sign=6af2c26ff4a45e55334189301c867384&type=video_thumb',
        },
    }, {
        'url': 'https://daftsex.com/watch/-156601359_456242791',
        'info_dict': {
            'id': '-156601359_456242791',
            'ext': 'mp4',
            'title': 'Skye Blue - Dinner And A Show',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        try:
            title = get_elements_by_class('heading', webpage)[-1]
            duration = parse_duration(self._search_regex(
                r'Duration: ((?:[0-9]{2}:){0,2}[0-9]{2})',
                webpage, 'duration', fatal=False))
            views = parse_count(self._search_regex(
                r'Views: ([0-9 ]+)',
                webpage, 'views', fatal=False))

            player_hash = self._search_regex(
                r'DaxabPlayer\.Init\({[\s\S]*hash:\s*"([0-9a-zA-Z_\-]+)"[\s\S]*}',
                webpage, 'player hash')
            player_color = self._search_regex(
                r'DaxabPlayer\.Init\({[\s\S]*color:\s*"([0-9a-z]+)"[\s\S]*}',
                webpage, 'player color', fatal=False) or ''

            embed_page = self._download_webpage(
                'https://daxab.com/player/%s?color=%s' % (player_hash, player_color),
                video_id, headers={'Referer': url})
            video_params = self._parse_json(
                self._search_regex(
                    r'window\.globParams\s*=\s*({[\S\s]+})\s*;\s*<\/script>',
                    embed_page, 'video parameters'),
                video_id, transform_source=js_to_json)

            server_domain = 'https://%s' % compat_b64decode(video_params['server'][::-1]).decode('utf-8')
            formats = []
            for format_id, format_data in video_params['video']['cdn_files'].items():
                ext, height = format_id.split('_')
                extra_quality_data = format_data.split('.')[-1]
                url = f'{server_domain}/videos/{video_id.replace("_", "/")}/{height}.mp4?extra={extra_quality_data}'
                formats.append({
                    'format_id': format_id,
                    'url': url,
                    'height': int_or_none(height),
                    'ext': ext,
                })
            self._sort_formats(formats)

            thumbnail = try_get(video_params,
                                lambda vi: 'https:' + compat_b64decode(vi['video']['thumb']).decode('utf-8'))

            return {
                'id': video_id,
                'title': title,
                'formats': formats,
                'duration': duration,
                'thumbnail': thumbnail,
                'view_count': views,
                'age_limit': 18,
            }

        except KeyError:
            title = self._html_search_meta('name', webpage, 'Title', fatal=False)
            upload_date = unified_timestamp(self._html_search_meta('uploadDate', webpage, 'Upload Date', default=None))
            description = self._html_search_meta('description', webpage, 'Description', default=None)

            global_embed_url = self._search_regex(
                r'<script[^<]+?window.globEmbedUrl\s*=\s*\'((?:https?:)?//(?:daxab\.com|dxb\.to|[^/]+/player)/[^\']+)\'',
                webpage, 'global Embed url')
            hash = self._search_regex(
                r'<script id="data-embed-video[^<]+?hash: "([^"]+)"[^<]*</script>', webpage, 'Hash')

            embed_url = global_embed_url + hash

            if VKIE.suitable(embed_url):
                return self.url_result(embed_url, VKIE.ie_key(), video_id)

            embed_page = self._download_webpage(
                embed_url, video_id, 'Downloading embed webpage', headers={'Referer': url})

            glob_params = self._parse_json(self._search_regex(
                r'<script id="globParams">[^<]*window.globParams = ([^;]+);[^<]+</script>',
                embed_page, 'Global Parameters'), video_id, transform_source=js_to_json)
            host_name = compat_b64decode(glob_params['server'][::-1]).decode()

            item = self._download_json(
                f'https://{host_name}/method/video.get/{video_id}', video_id,
                headers={'Referer': url}, query={
                    'token': glob_params['video']['access_token'],
                    'videos': video_id,
                    'ckey': glob_params['c_key'],
                    'credentials': glob_params['video']['credentials'],
                })['response']['items'][0]

            formats = []
            for f_id, f_url in item.get('files', {}).items():
                if f_id == 'external':
                    return self.url_result(f_url)
                ext, height = f_id.split('_')
                height_extra_key = traverse_obj(glob_params, ('video', 'partial', 'quality', height))
                if height_extra_key:
                    formats.append({
                        'format_id': f'{height}p',
                        'url': f'https://{host_name}/{f_url[8:]}&videos={video_id}&extra_key={height_extra_key}',
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
