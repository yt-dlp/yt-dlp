# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_kwargs,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
)


class ViuBaseIE(InfoExtractor):
    def _real_initialize(self):
        viu_auth_res = self._request_webpage(
            'https://www.viu.com/api/apps/v2/authenticate', None,
            'Requesting Viu auth', query={
                'acct': 'test',
                'appid': 'viu_desktop',
                'fmt': 'json',
                'iid': 'guest',
                'languageid': 'default',
                'platform': 'desktop',
                'userid': 'guest',
                'useridtype': 'guest',
                'ver': '1.0'
            }, headers=self.geo_verification_headers())
        self._auth_token = viu_auth_res.info()['X-VIU-AUTH']

    def _call_api(self, path, *args, **kwargs):
        headers = self.geo_verification_headers()
        headers.update({
            'X-VIU-AUTH': self._auth_token
        })
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        response = self._download_json(
            'https://www.viu.com/api/' + path, *args,
            **compat_kwargs(kwargs))['response']
        if response.get('status') != 'success':
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, response['message']), expected=True)
        return response


class ViuIE(ViuBaseIE):
    _VALID_URL = r'(?:viu:|https?://[^/]+\.viu\.com/[a-z]{2}/media/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.viu.com/en/media/1116705532?containerId=playlist-22168059',
        'info_dict': {
            'id': '1116705532',
            'ext': 'mp4',
            'title': 'Citizen Khan - Ep 1',
            'description': 'md5:d7ea1604f49e5ba79c212c551ce2110e',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to India',
    }, {
        'url': 'https://www.viu.com/en/media/1130599965',
        'info_dict': {
            'id': '1130599965',
            'ext': 'mp4',
            'title': 'Jealousy Incarnate - Episode 1',
            'description': 'md5:d3d82375cab969415d2720b6894361e9',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to Indonesia',
    }, {
        'url': 'https://india.viu.com/en/media/1126286865',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._call_api(
            'clip/load', video_id, 'Downloading video data', query={
                'appid': 'viu_desktop',
                'fmt': 'json',
                'id': video_id
            })['item'][0]

        title = video_data['title']

        m3u8_url = None
        url_path = video_data.get('urlpathd') or video_data.get('urlpath')
        tdirforwhole = video_data.get('tdirforwhole')
        # #EXT-X-BYTERANGE is not supported by native hls downloader
        # and ffmpeg (#10955)
        # hls_file = video_data.get('hlsfile')
        hls_file = video_data.get('jwhlsfile')
        if url_path and tdirforwhole and hls_file:
            m3u8_url = '%s/%s/%s' % (url_path, tdirforwhole, hls_file)
        else:
            # m3u8_url = re.sub(
            #     r'(/hlsc_)[a-z]+(\d+\.m3u8)',
            #     r'\1whe\2', video_data['href'])
            m3u8_url = video_data['href']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        self._sort_formats(formats)

        subtitles = {}
        for key, value in video_data.items():
            mobj = re.match(r'^subtitle_(?P<lang>[^_]+)_(?P<ext>(vtt|srt))', key)
            if not mobj:
                continue
            subtitles.setdefault(mobj.group('lang'), []).append({
                'url': value,
                'ext': mobj.group('ext')
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'series': video_data.get('moviealbumshowname'),
            'episode': title,
            'episode_number': int_or_none(video_data.get('episodeno')),
            'duration': int_or_none(video_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
        }


class ViuPlaylistIE(ViuBaseIE):
    IE_NAME = 'viu:playlist'
    _VALID_URL = r'https?://www\.viu\.com/[^/]+/listing/playlist-(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.viu.com/en/listing/playlist-22461380',
        'info_dict': {
            'id': '22461380',
            'title': 'The Good Wife',
        },
        'playlist_count': 16,
        'skip': 'Geo-restricted to Indonesia',
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_data = self._call_api(
            'container/load', playlist_id,
            'Downloading playlist info', query={
                'appid': 'viu_desktop',
                'fmt': 'json',
                'id': 'playlist-' + playlist_id
            })['container']

        entries = []
        for item in playlist_data.get('item', []):
            item_id = item.get('id')
            if not item_id:
                continue
            item_id = compat_str(item_id)
            entries.append(self.url_result(
                'viu:' + item_id, 'Viu', item_id))

        return self.playlist_result(
            entries, playlist_id, playlist_data.get('title'))


class ViuOTTIE(InfoExtractor):
    IE_NAME = 'viu:ott'
    _VALID_URL = r'https?://(?:www\.)?viu\.com/ott/(?P<country_code>[a-z]{2})/[a-z]{2}-[a-z]{2}/vod/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.viu.com/ott/sg/en-us/vod/3421/The%20Prime%20Minister%20and%20I',
        'info_dict': {
            'id': '3421',
            'ext': 'mp4',
            'title': 'A New Beginning',
            'description': 'md5:1e7486a619b6399b25ba6a41c0fe5b2c',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to Singapore',
    }, {
        'url': 'http://www.viu.com/ott/hk/zh-hk/vod/7123/%E5%A4%A7%E4%BA%BA%E5%A5%B3%E5%AD%90',
        'info_dict': {
            'id': '7123',
            'ext': 'mp4',
            'title': '這就是我的生活之道',
            'description': 'md5:4eb0d8b08cf04fcdc6bbbeb16043434f',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to Hong Kong',
    }]

    _AREA_ID = {
        'HK': 1,
        'SG': 2,
        'TH': 4,
        'PH': 5,
    }

    def _real_extract(self, url):
        country_code, video_id = re.match(self._VALID_URL, url).groups()

        query = {
            'r': 'vod/ajax-detail',
            'platform_flag_label': 'web',
            'product_id': video_id,
        }

        area_id = self._AREA_ID.get(country_code.upper())
        if area_id:
            query['area_id'] = area_id

        product_data = self._download_json(
            'http://www.viu.com/ott/%s/index.php' % country_code, video_id,
            'Downloading video info', query=query)['data']

        video_data = product_data.get('current_product')
        if not video_data:
            raise ExtractorError('This video is not available in your region.', expected=True)

        stream_data = self._download_json(
            'https://d1k2us671qcoau.cloudfront.net/distribute_web_%s.php' % country_code,
            video_id, 'Downloading stream info', query={
                'ccs_product_id': video_data['ccs_product_id'],
            }, headers={
                'Referer': url,
                'Origin': re.search(r'https?://[^/]+', url).group(0),
            })['data']['stream']

        stream_sizes = stream_data.get('size', {})
        formats = []
        for vid_format, stream_url in stream_data.get('url', {}).items():
            height = int_or_none(self._search_regex(
                r's(\d+)p', vid_format, 'height', default=None))
            formats.append({
                'format_id': vid_format,
                'url': stream_url,
                'height': height,
                'ext': 'mp4',
                'filesize': int_or_none(stream_sizes.get(vid_format))
            })
        self._sort_formats(formats)

        subtitles = {}
        for sub in video_data.get('subtitle', []):
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('name'), []).append({
                'url': sub_url,
                'ext': 'srt',
            })

        title = video_data['synopsis'].strip()

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'series': product_data.get('series', {}).get('name'),
            'episode': title,
            'episode_number': int_or_none(video_data.get('number')),
            'duration': int_or_none(stream_data.get('duration')),
            'thumbnail': video_data.get('cover_image_url'),
            'formats': formats,
            'subtitles': subtitles,
        }
