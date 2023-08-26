import re
import urllib.parse

from .common import InfoExtractor
from ..utils import js_to_json, str_or_none, traverse_obj


class SubstackIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<username>[\w-]+)\.substack\.com/p/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://haleynahman.substack.com/p/i-made-a-vlog?s=r',
        'md5': 'f27e4fc6252001d48d479f45e65cdfd5',
        'info_dict': {
            'id': '47660949',
            'ext': 'mp4',
            'title': 'I MADE A VLOG',
            'description': 'md5:9248af9a759321e1027226f988f54d96',
            'thumbnail': 'md5:bec758a34d8ee9142d43bcebdf33af18',
            'uploader': 'Maybe Baby',
            'uploader_id': '33628',
        }
    }, {
        'url': 'https://haleynahman.substack.com/p/-dear-danny-i-found-my-boyfriends?s=r',
        'md5': '0a63eacec877a1171a62cfa69710fcea',
        'info_dict': {
            'id': '51045592',
            'ext': 'mpga',
            'title': "🎧 Dear Danny: I found my boyfriend's secret Twitter account",
            'description': 'md5:a57f2439319e56e0af92dd0c95d75797',
            'thumbnail': 'md5:daa40b6b79249417c14ff8103db29639',
            'uploader': 'Maybe Baby',
            'uploader_id': '33628',
        }
    }, {
        'url': 'https://andrewzimmern.substack.com/p/mussels-with-black-bean-sauce-recipe',
        'md5': 'fd3c07077b02444ff0130715b5f632bb',
        'info_dict': {
            'id': '47368578',
            'ext': 'mp4',
            'title': 'Mussels with Black Bean Sauce: Recipe of the Week #7',
            'description': 'md5:b96234a2906c7d854d5229818d889515',
            'thumbnail': 'md5:e30bfaa9da40e82aa62354263a9dd232',
            'uploader': "Andrew Zimmern's Spilled Milk ",
            'uploader_id': '577659',
        }
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        if not re.search(r'<script[^>]+src=["\']https://substackcdn.com/[^"\']+\.js', webpage):
            return

        mobj = re.search(r'{[^}]*["\']subdomain["\']\s*:\s*["\'](?P<subdomain>[^"]+)', webpage)
        if mobj:
            parsed = urllib.parse.urlparse(url)
            yield parsed._replace(netloc=f'{mobj.group("subdomain")}.substack.com').geturl()
            raise cls.StopExtraction()

    def _extract_video_formats(self, video_id, username):
        formats, subtitles = [], {}
        for video_format in ('hls', 'mp4'):
            video_url = f'https://{username}.substack.com/api/v1/video/upload/{video_id}/src?type={video_format}'

            if video_format == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': video_url,
                    'ext': video_format,
                })

        return formats, subtitles

    def _real_extract(self, url):
        display_id, username = self._match_valid_url(url).group('id', 'username')
        webpage = self._download_webpage(url, display_id)

        webpage_info = self._parse_json(self._search_json(
            r'window\._preloads\s*=\s*JSON\.parse\(', webpage, 'json string',
            display_id, transform_source=js_to_json, contains_pattern=r'"{(?s:.+)}"'), display_id)

        post_type = webpage_info['post']['type']
        formats, subtitles = [], {}
        if post_type == 'podcast':
            formats, subtitles = [{'url': webpage_info['post']['podcast_url']}], {}
        elif post_type == 'video':
            formats, subtitles = self._extract_video_formats(webpage_info['post']['videoUpload']['id'], username)
        else:
            self.raise_no_formats(f'Page type "{post_type}" is not supported')

        return {
            'id': str(webpage_info['post']['id']),
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(webpage_info, ('post', 'title')),
            'description': traverse_obj(webpage_info, ('post', 'description')),
            'thumbnail': traverse_obj(webpage_info, ('post', 'cover_image')),
            'uploader': traverse_obj(webpage_info, ('pub', 'name')),
            'uploader_id': str_or_none(traverse_obj(webpage_info, ('post', 'publication_id'))),
        }
