import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    remove_start,
    update_url_query,
    urljoin,
)
from ..utils.traversal import traverse_obj


class StageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?stage\.in/(?:[^/]+/){4}[\w-]+-(?P<id>[^/?#]+)'
    _TESTS = [{
        # Movie
        'url': 'https://www.stage.in/hi/haryanvi/movie/watch/khejdi-20073',
        'info_dict': {
            'id': '20073',
            'ext': 'mp4',
            'title': 'Khejdi',
            'description': 'md5:b851a60afec89ec26167b6c1803bfddb',
            'duration': 5513,
            'thumbnail': r're:https?://[^/]+/.+\.(?:webp|jpe?g|png)',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Login required',
    }, {
        # Episode
        'url': 'https://www.stage.in/hi/haryanvi/show/watch/bhakk-16566/1',
        'info_dict': {
            'id': '16566',
            'ext': 'mp4',
            'title': 'Bhakk ',
            'description': 'md5:11dcdb1df7c3ac4a5dbe3aa08fdfa4c4',
            'thumbnail': r're:https?://[^/]+/.+\.(?:webp|jpe?g|png)',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Login required',
    }]

    @staticmethod
    def signed_params(data, signed_key='signedCookies', as_string=False):
        query = {}
        for key, value in data[signed_key].items():
            query[remove_start(key, 'CloudFront-')] = value
        return urllib.parse.urlencode(query, doseq=True) if as_string else query

    def sign_url(self, base_url, data, key='signedCookies'):
        return update_url_query(base_url, self.signed_params(data, key))

    # TODO: Remove this when PR https://github.com/yt-dlp/yt-dlp/pull/15541 resolved
    def get_nextjs_data(self, webpage, video_id):
        path = lambda _, x: x.get('contentDetail')
        next_data = self._search_nextjs_v13_data(webpage, video_id)

        data = traverse_obj(next_data, (path, {dict}, any))
        if data:
            return data

        for next_script in re.findall(r'<script\b[^>]*>self\.__next_f\.push\((\[.+?\])\)</script>', webpage):
            if 'signedURLDetails' in next_script:
                next_script = next_script.encode().decode('unicode_escape')
                next_data = self._search_json(
                    r':',
                    next_script,
                    'next_data',
                    video_id,
                    contains_pattern=r'(\[\[[\s\S]+?\]\])')
                break

        if not next_data:
            raise ExtractorError('Unable to extract nextjs v13 data')

        data = traverse_obj(next_data, (..., path, {dict}, any))
        if not data:
            raise ExtractorError('Unable to extract data')

        return data

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        if '/login' in self._html_search_meta('__next-page-redirect', webpage, default=''):
            self.raise_login_required(method='cookies')

        data = self.get_nextjs_data(webpage, video_id)
        content_data = data.get('contentDetail')

        formats = []
        media = data.get('signedURLDetails')
        for obj in ('signedObjectH265', 'signedObject'):
            signed_object = media.get(obj)
            signed_url = signed_object.get('signedUrl')
            if not signed_url:
                url = signed_object.get('url')
                signed_url = self.sign_url(url, signed_object)
            fmts = self._extract_m3u8_formats(signed_url, video_id)

            for f in fmts:
                f['url'] = self.sign_url(f.get('url'), signed_object)
                f['extra_param_to_segment_url'] = self.signed_params(signed_object, as_string=True)
                formats.append(f)

        subtitles = {}
        for lang, sub_path in content_data.get('subtitle', {}).items():
            subtitle_base_url = 'https://media.stage.in/episode/srt'
            if not sub_path:
                continue
            subtitles.setdefault(lang, []).append({
                'url': urljoin(subtitle_base_url, sub_path),
                'ext': 'srt',
            })

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': content_data.get('description') or self._og_search_description(webpage),
            'duration': content_data.get('duration'),
            'thumbnail': content_data.get('largeTrailerThumbnail') or content_data.get('trailerThumbnail'),
            'formats': formats,
            'subtitles': subtitles,
        }
