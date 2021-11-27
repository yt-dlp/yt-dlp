# coding: utf-8

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    try_get,
)


class RedGifsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|thumbs2?)\.)?redgifs\.com/(?:watch/)?(?P<id>[^-/?#\.]+)'
    _FORMATS = {
        'gif': 250,
        'sd': 480,
        'hd': None,
    }
    _TESTS = [{
        'url': 'https://www.redgifs.com/watch/squeakyhelplesswisent',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }, {
        'url': 'https://thumbs2.redgifs.com/SqueakyHelplessWisent-mobile.mp4#t=0',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).lower()

        video_info = self._download_json(
            'https://api.redgifs.com/v2/gifs/%s' % video_id,
            video_id, 'Downloading video info')
        if 'error' in video_info:
            raise ExtractorError(f'RedGifs said: {video_info["error"]}', expected=True)

        gif = video_info['gif']
        urls = gif['urls']

        quality = qualities(tuple(self._FORMATS.keys()))

        orig_height = int_or_none(gif.get('height'))
        aspect_ratio = try_get(gif, lambda x: orig_height / x['width'])

        formats = []
        for format_id, height in self._FORMATS.items():
            video_url = urls.get(format_id)
            if not video_url:
                continue
            height = min(orig_height, height or orig_height)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': height * aspect_ratio if aspect_ratio else None,
                'height': height,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': ' '.join(gif.get('tags') or []) or 'RedGifs',
            'timestamp': int_or_none(gif.get('createDate')),
            'uploader': gif.get('userName'),
            'duration': int_or_none(gif.get('duration')),
            'view_count': int_or_none(gif.get('views')),
            'like_count': int_or_none(gif.get('likes')),
            'categories': gif.get('tags') or [],
            'age_limit': 18,
            'formats': formats,
        }


def _parse_gif_entry(gif_data):
    video_id = gif_data["id"]
    title = " ".join(gif_data['tags'])
    formats = [
        {
            "format_id": "gif",
            "url": gif_data["urls"]["gif"]
        },
        {
            "format_id": "sd",
            "url": gif_data["urls"]["sd"]
        },
        {
            "format_id": "hd",
            "url": gif_data["urls"]["hd"]
        }
    ]
    webpage_url = "https://redgifs.com/watch/{}".format(video_id)

    return {
        'id': video_id,
        'title': title,
        'age_limit': 18,
        'formats': formats,
        'timestamp': gif_data.get('createDate'),
        'view_count': int_or_none(gif_data.get('views')),
        'uploader': gif_data.get('userName'),
        'webpage_url': webpage_url,
        'tags': gif_data.get('tags')
    }


class RedGifsSearchIE(InfoExtractor):
    IE_DESC = 'Redgifs search'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/browse\?(?P<query>.*)'
    _TESTS = [
        {
            'url': 'https://www.redgifs.com/browse?tags=Lesbian',
            'info_dict': {
                'id': 'tags=Lesbian',
                'title': 'Lesbian',
                'description': 'Redgifs search for Lesbian, ordered by trending'
            },
            'playlist_mincount': 19,
        },
        {
            'url': 'https://www.redgifs.com/browse?type=g&order=latest&tags=Lesbian',
            'info_dict': {
                'id': 'type=g&order=latest&tags=Lesbian',
                'title': 'Lesbian',
                'description': 'Redgifs search for Lesbian, ordered by latest'
            },
            'playlist_mincount': 19,
        }
    ]

    def _real_extract(self, url):
        query_str = self._match_valid_url(url).group("query")

        query = compat_parse_qs(query_str)
        if not query.get('tags'):
            raise ExtractorError('Invalid query tags', expected=True)

        tags = query.get("tags")[0]
        order = query.get("order", ("trending",))[0]
        page = query.get("page", (1,))[0]
        api_query = {
            "search_text": tags,
            "order": order,
            "page": page
        }
        if query.get("type"):
            api_query["type"] = query.get("type")[0]

        data = self._download_json(
            "https://api.redgifs.com/v2/gifs/search",
            query_str,
            query=api_query
        )
        if 'error' in data:
            raise ExtractorError(f'RedGifs said: {data["error"]}', expected=True)

        entries = [_parse_gif_entry(entry) for entry in data['gifs']]
        title = tags
        description = "Redgifs search for {}, ordered by {}".format(tags, order)

        return self.playlist_result(
            entries,
            playlist_id=query_str,
            playlist_title=title,
            playlist_description=description
        )
