import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    mimetype2ext,
    parse_codecs,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj
from ..version import __version__ as YT_DLP_VERSION


class WikimediaIE(InfoExtractor):
    IE_NAME = 'wikimedia.org'
    _VALID_URL = r'https?://commons\.wikimedia\.org/wiki/File:(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://commons.wikimedia.org/wiki/File:Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS.webm',
        'info_dict': {
            'ext': 'webm',
            'id': '83227919',
            'display_id': 'Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS.webm',
            'title': 'Die Temperaturkurve der Erde (ZDF, Terra X) 720p HD 50FPS',
            'description': 'Climate change, Temperature in history of Earth, Video of Terra X.',
            'uploader': 'ZDF Terra X Redaktion',
            'duration': 45.327,
            'categories': 'count:16',
            'timestamp': 1597848846,
            'upload_date': '20200819',
            'license': 'Creative Commons Attribution 4.0',
            'subtitles': 'count:3',
        },
    }, {
        # url needs unquoting
        'url': 'https://commons.wikimedia.org/wiki/File:Two-toed_sloth_rail_walking_%E4%BA%8C%E8%B6%BE%E6%A8%B9%E7%8D%BA%E7%88%AC%E8%A1%8C_(HD).webm',
        'info_dict': {
            'ext': 'webm',
            'id': '165082300',
            'display_id': 'Two-toed_sloth_rail_walking_%E4%BA%8C%E8%B6%BE%E6%A8%B9%E7%8D%BA%E7%88%AC%E8%A1%8C_(HD).webm',
            'title': 'Two-toed sloth rail walking 二趾樹獺爬行 (HD)',
            'description': 'md5:3c32e4c7f6103dde4ecd9e9313b23526',
            'uploader': 'Tvpuppy',
            'duration': 25.688,
            'categories': 'count:8',
            'timestamp': 1747012249,
            'upload_date': '20250512',
            'license': 'Creative Commons Attribution 3.0',
        },
    }]

    _HTTP_HEADERS = {
        # Faking a browser user-agent leads to being blocked with a 403.
        # Follow robot policy as per https://wikitech.wikimedia.org/wiki/Robot_policy
        'User-Agent': f'yt-dlp/{YT_DLP_VERSION} (https://github.com/yt-dlp/yt-dlp)',
    }

    @staticmethod
    def _parse_ext_and_codecs(s):
        if not s:
            return {}
        if mobj := re.match(r'(?P<mime>[^;]+)(?:;\s*codecs="(?P<codecs>[^"]+)")?', s):
            return {
                'ext': mimetype2ext(mobj.group('mime')),
                **parse_codecs(mobj.group('codecs')),
            }
        return {}

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_response = traverse_obj(self._download_json(
            'https://commons.wikimedia.org/w/api.php', display_id, query={
                'action': 'query',
                'format': 'json',
                'titles': f'File:{urllib.parse.unquote(display_id)}',
                'prop': 'videoinfo',
                'viprop': 'timestamp|user|url|size|derivatives|timedtext|extmetadata',
            }, headers=self._HTTP_HEADERS), ('query', 'pages', ..., {dict}, any))

        video_info = traverse_obj(api_response, ('videoinfo', 0, {dict}, {require('video info')}))
        formats = []
        if url_or_none(video_info.get('url')):
            formats.append({
                'url': video_info['url'],
                'format_id': 'source',
                'quality': 10,
                **traverse_obj(video_info, {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'filesize': ('size', {int_or_none}),
                }),
                'http_headers': self._HTTP_HEADERS,
            })
        for derivative in traverse_obj(video_info, ('derivatives', lambda _, v: url_or_none(v['src']))):
            formats.append({
                'url': derivative['src'],
                **traverse_obj(derivative, {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'tbr': ('bandwidth', {int_or_none(scale=1000)}),
                }),
                'http_headers': self._HTTP_HEADERS,
                **self._parse_ext_and_codecs(derivative.get('type')),
            })

        subtitles = {}
        for subtitle in traverse_obj(video_info, ('timedtext', lambda _, v: url_or_none(v['src']))):
            lang = subtitle.get('srclang') or 'unk'
            subtitles.setdefault(lang, []).append({
                'url': subtitle['src'],
                'ext': mimetype2ext(subtitle.get('type')),
                'http_headers': self._HTTP_HEADERS,
            })

        return {
            'id': str_or_none(api_response['pageid']),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_info, {
                'title': ('extmetadata', 'ObjectName', 'value', {str}),
                'timestamp': ('timestamp', {parse_iso8601}),
                'description': ('extmetadata', 'ImageDescription', 'value', {clean_html}),
                'uploader': ('user', {str}),
                'duration': ('duration', {float_or_none}),
                'license': ('extmetadata', 'UsageTerms', 'value', {str}),
                'categories': ('extmetadata', 'Categories', 'value', {lambda x: x.split('|')}, ..., {str.strip}, filter),
            }),
        }
