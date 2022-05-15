from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    traverse_obj,
)


class SubstackIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<username>[\w\d-]+).substack\.com/p/(?P<id>[\w\d-]+).*'
    _TESTS = [{
        'url': 'https://haleynahman.substack.com/p/i-made-a-vlog?s=r',
        'md5': 'f27e4fc6252001d48d479f45e65cdfd5',
        'info_dict': {
            'id': 'i-made-a-vlog',
            'ext': 'mp4',
            'title': 'I MADE A VLOG',
            'description': 'md5:10c01ff93439a62e70ce963b2aa0b7f6',
            'thumbnail': 'md5:bec758a34d8ee9142d43bcebdf33af18',
            'uploader': 'haleynahman',
        }
    }, {
        'url': 'https://haleynahman.substack.com/p/-dear-danny-i-found-my-boyfriends?s=r',
        'md5': '0a63eacec877a1171a62cfa69710fcea',
        'info_dict': {
            'id': '-dear-danny-i-found-my-boyfriends',
            'ext': 'mpga',
            'title': "🎧 Dear Danny: I found my boyfriend's secret Twitter account",
            'description': 'md5:a57f2439319e56e0af92dd0c95d75797',
            'thumbnail': 'md5:daa40b6b79249417c14ff8103db29639',
            'uploader': 'haleynahman',
        }
    }, {
        'url': 'https://andrewzimmern.substack.com/p/mussels-with-black-bean-sauce-recipe',
        'md5': 'fd3c07077b02444ff0130715b5f632bb',
        'info_dict': {
            'id': 'mussels-with-black-bean-sauce-recipe',
            'ext': 'mp4',
            'title': "Mussels with Black Bean Sauce: Recipe of the Week #7",
            'description': 'md5:b96234a2906c7d854d5229818d889515',
            'thumbnail': 'md5:e30bfaa9da40e82aa62354263a9dd232',
            'uploader': 'andrewzimmern',
        }
    }]

    def _extract_video_formats(self, video_id, username):
        formats, subtitles = [], []
        for video_format in ['hls', 'mp4']:
            video_url = f"https://{username}.substack.com/api/v1/video/upload/{video_id}/src?type={video_format}"

            if video_format == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.extend([{
                    'url': video_url,
                    'ext': video_format,
                }])

        return formats, subtitles

    def _real_extract(self, url):
        display_id = self._match_id(url)
        username = self._match_valid_url(url).group('username')

        webpage = self._download_webpage(url, display_id)

        preloads = self._parse_json(
            self._html_search_regex(r'<script[^>]*>\s*window\._preloads\s*=\s*({.+})\s*</script>', webpage, 'preloads'),
            video_id=display_id)

        post_info = preloads['post']
        post_type = post_info.get('type')

        formats, subtitles = [], []
        if post_type == "podcast":
            formats.append({
                'url': post_info.get('podcast_url'),
                'ext': determine_ext(post_info.get('podcast_url')),
            })
        elif post_type == "video":
            video_id = traverse_obj(post_info, ('videoUpload', 'id'))
            formats, subtitles = self._extract_video_formats(video_id, username)
        else:
            raise ExtractorError(f"Page type '{post_type}' is not supported")

        return {
            'id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': post_info.get('title'),
            'description': post_info.get('description'),
            'thumbnail': post_info.get('cover_image'),
            'uploader': username,
        }
