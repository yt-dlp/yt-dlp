from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    try_get,
    url_or_none,
)


class NineGagIE(InfoExtractor):
    IE_NAME = '9gag'
    _VALID_URL = r'https?://(?:www\.)?9gag\.com/gag/(?P<id>[^/?&#]+)'

    _TEST = {
        'url': 'https://9gag.com/gag/ae5Ag7B',
        'info_dict': {
            'id': 'ae5Ag7B',
            'ext': 'mp4',
            'title': 'Capybara Agility Training',
            'upload_date': '20191108',
            'timestamp': 1573237208,
            'categories': ['Awesome'],
            'tags': ['Weimaraner', 'American Pit Bull Terrier'],
            'duration': 44,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
        }
    }

    def _real_extract(self, url):
        post_id = self._match_id(url)
        post = self._download_json(
            'https://9gag.com/v1/post', post_id, query={
                'id': post_id
            })['data']['post']

        if post.get('type') != 'Animated':
            raise ExtractorError(
                'The given url does not contain a video',
                expected=True)

        title = post['title']

        duration = None
        formats = []
        thumbnails = []
        for key, image in (post.get('images') or {}).items():
            image_url = url_or_none(image.get('url'))
            if not image_url:
                continue
            ext = determine_ext(image_url)
            image_id = key.strip('image')
            common = {
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            }
            if ext in ('jpg', 'png'):
                webp_url = image.get('webpUrl')
                if webp_url:
                    t = common.copy()
                    t.update({
                        'id': image_id + '-webp',
                        'url': webp_url,
                    })
                    thumbnails.append(t)
                common.update({
                    'id': image_id,
                    'ext': ext,
                })
                thumbnails.append(common)
            elif ext in ('webm', 'mp4'):
                if not duration:
                    duration = int_or_none(image.get('duration'))
                common['acodec'] = 'none' if image.get('hasAudio') == 0 else None
                for vcodec in ('vp8', 'vp9', 'h265'):
                    c_url = image.get(vcodec + 'Url')
                    if not c_url:
                        continue
                    c_f = common.copy()
                    c_f.update({
                        'format_id': image_id + '-' + vcodec,
                        'url': c_url,
                        'vcodec': vcodec,
                    })
                    formats.append(c_f)
                common.update({
                    'ext': ext,
                    'format_id': image_id,
                })
                formats.append(common)
        self._sort_formats(formats)

        section = try_get(post, lambda x: x['postSection']['name'])

        tags = None
        post_tags = post.get('tags')
        if post_tags:
            tags = []
            for tag in post_tags:
                tag_key = tag.get('key')
                if not tag_key:
                    continue
                tags.append(tag_key)

        get_count = lambda x: int_or_none(post.get(x + 'Count'))

        return {
            'id': post_id,
            'title': title,
            'timestamp': int_or_none(post.get('creationTs')),
            'duration': duration,
            'formats': formats,
            'thumbnails': thumbnails,
            'like_count': get_count('upVote'),
            'dislike_count': get_count('downVote'),
            'comment_count': get_count('comments'),
            'age_limit': 18 if post.get('nsfw') == 1 else None,
            'categories': [section] if section else None,
            'tags': tags,
        }
